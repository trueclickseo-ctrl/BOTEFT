"""Hard execution controls independent of strategy logic."""
from __future__ import annotations
import os
from pathlib import Path

class TradingSafety:
    def __init__(self, kill_switch_file: Path | str = "runtime/KILL_SWITCH"):
        self.kill_switch_file = Path(kill_switch_file)
    def assert_order_allowed(self, environment: str) -> None:
        if self.kill_switch_file.exists(): raise PermissionError("Trading kill switch is active")
        if environment == "live" and os.getenv("SAXO_ALLOW_LIVE_TRADING") != "true":
            raise PermissionError("Live trading requires SAXO_ALLOW_LIVE_TRADING=true")
        if environment not in {"sim", "live"}: raise ValueError("Unknown Saxo environment")
    def activate_kill_switch(self) -> None:
        self.kill_switch_file.parent.mkdir(parents=True, exist_ok=True)
        self.kill_switch_file.write_text("Trading disabled by operator. Remove this file only after review.\n", encoding="utf-8")
