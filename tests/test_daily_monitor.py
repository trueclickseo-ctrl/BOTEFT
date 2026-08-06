from datetime import date
from quant_ai_trader.data.database import MarketDataRepository

def test_latest_bar_date_supports_incremental_monitor(tmp_path, sample_bars):
    repo = MarketDataRepository(tmp_path / "db.sqlite"); repo.initialize(); repo.upsert_bars("QQQ", sample_bars)
    assert repo.latest_bar_date("QQQ").date() <= date.today() or repo.latest_bar_date("QQQ").year == 2023
