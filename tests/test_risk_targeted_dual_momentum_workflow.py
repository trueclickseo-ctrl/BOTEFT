from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.risk_targeted_dual_momentum import run


def test_risk_targeted_dual_momentum_workflow_records_result(tmp_path, sample_bars, monkeypatch):
    monkeypatch.chdir(tmp_path); repo = MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize()
    for symbol in ("SPY", "QQQ", "GLD"): repo.upsert_bars(symbol, sample_bars)
    assert run(["SPY", "QQQ", "GLD"])["research_only"] == 1.0
