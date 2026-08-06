from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.buy_and_hold import run
def test_buy_and_hold_records_benchmark(tmp_path, sample_bars, monkeypatch):
    monkeypatch.chdir(tmp_path); repo = MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize(); repo.upsert_bars("QQQ", sample_bars)
    assert "total_return" in run("QQQ")
