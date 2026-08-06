import numpy as np

from quant_ai_trader.dashboard.data_service import build_rankings, run_model_backtest
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset, model_feature_columns
from quant_ai_trader.models.model_manager import ModelArtifact


class AlwaysBullishModel:
    def predict_proba(self, features):
        return np.tile([.2, .8], (len(features), 1))


def test_rankings_and_model_backtest_use_stored_data(tmp_path, sample_bars):
    repository = MarketDataRepository(tmp_path / "market.sqlite3")
    repository.initialize()
    repository.upsert_bars("SPY", sample_bars)
    repository.upsert_bars("QQQ", sample_bars)
    feature_columns = model_feature_columns(build_feature_dataset(sample_bars, spy_bars=sample_bars))
    artifact = ModelArtifact.create(AlwaysBullishModel(), feature_columns, .06, .03, 30, {})
    rankings = build_rankings(repository, artifact)
    assert rankings.iloc[0]["symbol"] == "QQQ"
    result = run_model_backtest(repository, artifact, "QQQ")
    assert not result.equity_curve.empty
