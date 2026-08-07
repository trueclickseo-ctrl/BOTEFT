from urllib.parse import parse_qs, urlparse

import pytest

from quant_ai_trader.execution.saxo_oauth import SaxoOAuthClient, SaxoOAuthSettings


class Response:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): pass
    def json(self): return self.payload


class Session:
    def __init__(self): self.posts = []
    def post(self, url, data, timeout):
        self.posts.append((url, data, timeout))
        return Response({"access_token": "access", "refresh_token": "refresh", "expires_in": 1200})


def test_pkce_authorization_exchange_and_refresh(tmp_path):
    session = Session()
    settings = SaxoOAuthSettings("app-key", token_path=tmp_path / "tokens.json")
    client = SaxoOAuthClient(settings, session)
    query = parse_qs(urlparse(client.authorization_url()).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == [settings.redirect_uri]
    token = client.exchange("auth-code", query["state"][0])
    assert token["access_token"] == "access"
    assert session.posts[0][1]["code_verifier"]
    assert client.access_token() == "access"
    token["expires_at"] = 0
    settings.token_path.write_text(__import__("json").dumps(token), encoding="utf-8")
    assert client.access_token() == "access"
    assert session.posts[-1][1]["grant_type"] == "refresh_token"


def test_pkce_rejects_unknown_state(tmp_path):
    client = SaxoOAuthClient(SaxoOAuthSettings("app-key", token_path=tmp_path / "tokens.json"), Session())
    with pytest.raises(PermissionError, match="Invalid or expired"):
        client.exchange("code", "wrong-state")
