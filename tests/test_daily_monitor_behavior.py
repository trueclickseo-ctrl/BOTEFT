from unittest.mock import patch
from datetime import date, timedelta
from quant_ai_trader.workflows.daily_monitor import run
from quant_ai_trader.data.database import MarketDataRepository
import pandas as pd

def test_monitor_treats_no_completed_chart_bar_as_zero_update(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path); monkeypatch.setenv("SAXO_ACCESS_TOKEN", "token"); monkeypatch.setenv("SAXO_INSTRUMENTS_JSON", '{"SPY":{"uic":1,"asset_type":"Etf"},"QQQ":{"uic":2,"asset_type":"Etf"}}')
    with patch("quant_ai_trader.workflows.daily_monitor.sync_symbol", side_effect=ValueError("No chart samples returned by Saxo for SPY")), patch("quant_ai_trader.workflows.daily_monitor.validate_breakout", return_value={}):
        assert run(["SPY", "QQQ"])["updated_bars"] == {"SPY": 0, "QQQ": 0}


def test_monitor_never_requests_an_in_progress_daily_bar(monkeypatch, tmp_path, sample_bars):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SAXO_ACCESS_TOKEN", "token")
    monkeypatch.setenv("SAXO_INSTRUMENTS_JSON", '{"SPY":{"uic":1,"asset_type":"Etf"},"QQQ":{"uic":2,"asset_type":"Etf"}}')
    repo = MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize()
    yesterday = pd.Timestamp(date.today() - timedelta(days=1))
    bars = sample_bars.tail(1).copy(); bars.index = pd.DatetimeIndex([yesterday])
    repo.upsert_bars("SPY", bars); repo.upsert_bars("QQQ", bars)
    with patch("quant_ai_trader.workflows.daily_monitor.sync_symbol") as sync, patch("quant_ai_trader.workflows.daily_monitor.validate_breakout", return_value={}):
        result = run(["SPY", "QQQ"])
    assert result["updated_bars"] == {"SPY": 0, "QQQ": 0}
    sync.assert_not_called()
