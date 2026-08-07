from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.cross_sectional_ml import build_dataset
from quant_ai_trader.features.feature_pipeline import model_feature_columns

def test_cross_sectional_ml_label_is_date_relative(tmp_path,sample_bars,monkeypatch):
    monkeypatch.chdir(tmp_path); repo=MarketDataRepository("data/db.sqlite"); repo.initialize()
    for symbol in ("SPY","QQQ","GLD"): repo.upsert_bars(symbol,sample_bars)
    dataset=build_dataset(repo,["QQQ","GLD"])
    assert "target_hit_before_stop" in dataset and dataset.index.nlevels==2 and "forward_return" not in model_feature_columns(dataset)
