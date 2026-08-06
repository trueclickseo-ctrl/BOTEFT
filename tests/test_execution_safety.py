import pytest
from quant_ai_trader.execution.safety import TradingSafety

def test_kill_switch_blocks_simulation_orders(tmp_path):
    safety = TradingSafety(tmp_path / "KILL_SWITCH")
    safety.assert_order_allowed("sim")
    safety.activate_kill_switch()
    with pytest.raises(PermissionError, match="kill switch"):
        safety.assert_order_allowed("sim")

def test_live_trading_requires_explicit_environment_flag(tmp_path, monkeypatch):
    safety = TradingSafety(tmp_path / "KILL_SWITCH")
    with pytest.raises(PermissionError, match="SAXO_ALLOW_LIVE_TRADING"):
        safety.assert_order_allowed("live")
    monkeypatch.setenv("SAXO_ALLOW_LIVE_TRADING", "true")
    safety.assert_order_allowed("live")
