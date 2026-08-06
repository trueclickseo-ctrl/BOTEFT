from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_walkforward import run
def test_breakout_walkforward_returns_fold_summary(tmp_path, sample_bars, monkeypatch):
    monkeypatch.chdir(tmp_path); repo = MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize()
    repo.upsert_bars("SPY", sample_bars); repo.upsert_bars("QQQ", sample_bars)
    assert run("QQQ", folds=2)["folds"] == 2.0
