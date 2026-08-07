from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.core_satellite import run


def test_core_satellite_runs_on_stored_history(tmp_path, sample_bars, monkeypatch):
    monkeypatch.chdir(tmp_path); repo = MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize()
    for symbol in ("SPY", "QQQ", "GLD"): repo.upsert_bars(symbol, sample_bars)
    result = run(["SPY", "QQQ", "GLD"], folds=2)
    assert result["core_weight"] == .5 and len(result["fold_details"]) == 2
