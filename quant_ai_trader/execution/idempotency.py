"""Persistent idempotency ledger for planned and submitted broker intents."""
from __future__ import annotations

import json
from pathlib import Path


class OrderIntentLedger:
    def __init__(self, path: Path | str = "runtime/order_intents.json") -> None:
        self.path = Path(path)

    def reserve(self, key: str) -> bool:
        records = self._load()
        if key in records:
            return False
        records[key] = {"status": "reserved"}
        self._save(records)
        return True

    def mark(self, key: str, status: str, order_id: str | None = None) -> None:
        records = self._load()
        if key not in records:
            raise KeyError(f"Unknown order intent: {key}")
        records[key] = {"status": status, "order_id": order_id}
        self._save(records)

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def _save(self, records: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(records, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)
