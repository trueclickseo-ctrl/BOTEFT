from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.diversified_core_satellite import run

def test_diversified_workflow_runs(tmp_path,sample_bars,monkeypatch):
    monkeypatch.chdir(tmp_path); repo=MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize()
    for s in ("SPY","QQQ","GLD"): repo.upsert_bars(s,sample_bars)
    result=run(["SPY","QQQ","GLD"],folds=2)
    assert result["research_only"]==1 and len(result["fold_details"])==2
