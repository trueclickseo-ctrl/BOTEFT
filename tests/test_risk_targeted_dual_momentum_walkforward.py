from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.risk_targeted_dual_momentum_walkforward import run


def test_risk_targeted_walkforward_produces_fixed_fold_summary(tmp_path, sample_bars, monkeypatch):
    monkeypatch.chdir(tmp_path); repo = MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize()
    for symbol in ("SPY", "QQQ", "GLD"): repo.upsert_bars(symbol, sample_bars)
    result = run(["SPY", "QQQ", "GLD"], folds=2)
    assert result["folds"] == 2 and len(result["fold_details"]) == 2 and "validation_status" in result
