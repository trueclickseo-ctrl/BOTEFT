from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.research import build_pooled_training_dataset

def test_pooled_dataset_uses_date_symbol_index(tmp_path, sample_bars):
    repo = MarketDataRepository(tmp_path / "db.sqlite"); repo.initialize()
    for symbol in ("SPY", "QQQ", "IWM"): repo.upsert_bars(symbol, sample_bars)
    data = build_pooled_training_dataset(repo, ["QQQ", "IWM"], Settings(database_path=tmp_path / "db.sqlite"))
    assert data.index.names == ["date", "symbol"]
