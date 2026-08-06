from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.research import build_training_dataset

def test_build_training_dataset_from_stored_bars(tmp_path, sample_bars):
    repo = MarketDataRepository(tmp_path / "market.sqlite"); repo.initialize()
    repo.upsert_bars("SPY", sample_bars); repo.upsert_bars("QQQ", sample_bars)
    dataset = build_training_dataset(repo, "QQQ", Settings(database_path=tmp_path / "market.sqlite"))
    assert "target_hit_before_stop" in dataset
    assert dataset["target_hit_before_stop"].notna().sum() > 0
