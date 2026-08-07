from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.core_satellite_allocation import run


def test_candidate_allocation_plan_never_creates_orders(tmp_path, sample_bars, monkeypatch):
    monkeypatch.chdir(tmp_path); repo = MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize()
    for symbol in ("SPY", "QQQ", "GLD"): repo.upsert_bars(symbol, sample_bars)
    result = run(["SPY", "QQQ", "GLD"])
    assert result["orders_created"] is False and "CASH" in result["weights"]
