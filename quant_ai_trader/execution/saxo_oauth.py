"""Saxo OAuth2 PKCE client with local, git-ignored token persistence."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode


@dataclass(frozen=True)
class SaxoOAuthSettings:
    app_key: str
    redirect_uri: str = "http://localhost:8000/auth/saxo/callback"
    environment: str = "sim"
    token_path: Path = Path("data/saxo_oauth_tokens.json")

    @property
    def authorization_endpoint(self) -> str:
        return f"https://{'sim.' if self.environment == 'sim' else ''}logonvalidation.net/authorize"

    @property
    def token_endpoint(self) -> str:
        return f"https://{'sim.' if self.environment == 'sim' else ''}logonvalidation.net/token"

    @classmethod
    def from_environment(cls) -> "SaxoOAuthSettings":
        app_key = os.getenv("SAXO_APP_KEY")
        if not app_key:
            raise RuntimeError("SAXO_APP_KEY is required for PKCE authentication")
        environment = os.getenv("SAXO_ENVIRONMENT", "sim").lower()
        if environment not in {"sim", "live"}:
            raise ValueError("SAXO_ENVIRONMENT must be either 'sim' or 'live'")
        return cls(
            app_key=app_key,
            redirect_uri=os.getenv("SAXO_REDIRECT_URI", "http://localhost:8000/auth/saxo/callback"),
            environment=environment,
            token_path=Path(os.getenv("SAXO_TOKEN_PATH", "data/saxo_oauth_tokens.json")),
        )


class SaxoOAuthClient:
    def __init__(self, settings: SaxoOAuthSettings, session=None) -> None:
        if settings.environment != "sim" and os.getenv("SAXO_ALLOW_LIVE_TRADING") != "true":
            raise PermissionError("OAuth setup is restricted to SIM unless live trading is explicitly enabled")
        if session is None:
            import requests
            session = requests.Session()
        self.settings = settings
        self.session = session
        self._pending: dict[str, str] = {}

    def authorization_url(self) -> str:
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        state = secrets.token_urlsafe(32)
        self._pending[state] = verifier
        query = urlencode({
            "response_type": "code", "client_id": self.settings.app_key,
            "redirect_uri": self.settings.redirect_uri, "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256",
        })
        return f"{self.settings.authorization_endpoint}?{query}"

    def exchange(self, code: str, state: str) -> dict:
        verifier = self._pending.pop(state, None)
        if not verifier:
            raise PermissionError("Invalid or expired OAuth state")
        response = self.session.post(self.settings.token_endpoint, data={
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": self.settings.redirect_uri,
            "client_id": self.settings.app_key, "code_verifier": verifier,
        }, timeout=30)
        response.raise_for_status()
        return self._save(response.json())

    def access_token(self) -> str:
        token = self._load()
        if not token:
            raise RuntimeError("Saxo OAuth login is required")
        if float(token.get("expires_at", 0)) <= time.time() + 60:
            token = self.refresh(token)
        return str(token["access_token"])

    def refresh(self, token: dict | None = None) -> dict:
        token = token or self._load()
        if not token or not token.get("refresh_token"):
            raise RuntimeError("No Saxo refresh token is available; log in again")
        response = self.session.post(self.settings.token_endpoint, data={
            "grant_type": "refresh_token", "refresh_token": token["refresh_token"],
            "client_id": self.settings.app_key,
        }, timeout=30)
        response.raise_for_status()
        return self._save(response.json())

    def status(self) -> dict[str, object]:
        token = self._load()
        return {"configured": bool(self.settings.app_key), "authenticated": bool(token),
                "expires_at": token.get("expires_at") if token else None,
                "environment": self.settings.environment}

    def _save(self, token: dict) -> dict:
        stored = dict(token)
        stored["expires_at"] = time.time() + int(stored.get("expires_in", 0))
        if not stored.get("access_token"):
            raise ValueError("Saxo token response did not contain access_token")
        self.settings.token_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.settings.token_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(stored), encoding="utf-8")
        temporary.replace(self.settings.token_path)
        return stored

    def _load(self) -> dict:
        if not self.settings.token_path.exists():
            return {}
        return json.loads(self.settings.token_path.read_text(encoding="utf-8"))
