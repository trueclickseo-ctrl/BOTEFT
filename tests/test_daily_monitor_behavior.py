from unittest.mock import patch
from quant_ai_trader.workflows.daily_monitor import run

def test_monitor_treats_no_completed_chart_bar_as_zero_update(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path); monkeypatch.setenv("SAXO_ACCESS_TOKEN", "token"); monkeypatch.setenv("SAXO_INSTRUMENTS_JSON", '{"SPY":{"uic":1,"asset_type":"Etf"},"QQQ":{"uic":2,"asset_type":"Etf"}}')
    with patch("quant_ai_trader.workflows.daily_monitor.sync_symbol", side_effect=ValueError("No chart samples returned by Saxo for SPY")), patch("quant_ai_trader.workflows.daily_monitor.validate_breakout", return_value={}):
        assert run(["SPY", "QQQ"])["updated_bars"] == {"SPY": 0, "QQQ": 0}
