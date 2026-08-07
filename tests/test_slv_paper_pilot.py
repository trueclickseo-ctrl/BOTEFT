from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.slv_paper_pilot import run

def test_slv_pilot_returns_non_submitting_no_trade_plan(tmp_path,sample_bars,monkeypatch):
    monkeypatch.chdir(tmp_path); repo=MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize()
    repo.upsert_bars("SPY",sample_bars); repo.upsert_bars("SLV",sample_bars)
    result=run()
    assert result["symbol"]=="SLV" and result["orders_created"] is False
