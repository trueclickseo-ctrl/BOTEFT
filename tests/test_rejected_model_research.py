from unittest.mock import patch
from quant_ai_trader.models.model_manager import ModelArtifact
from quant_ai_trader.models.train_model import TrainingResult
from quant_ai_trader.workflows.research import run

def test_rejected_model_is_reported_without_being_saved(tmp_path, sample_bars, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from quant_ai_trader.data.database import MarketDataRepository
    repo = MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize()
    repo.upsert_bars("SPY", sample_bars); repo.upsert_bars("QQQ", sample_bars)
    artifact = ModelArtifact.create(None, [], .06, .03, 30, {"roc_auc": .5, "average_precision": .1, "oos_observations": 200})
    with patch("quant_ai_trader.workflows.research.train_target_stop_model", return_value=TrainingResult(artifact, None)), patch("quant_ai_trader.workflows.research.run_model_backtest") as model_bt, patch("quant_ai_trader.workflows.research.run_momentum_backtest") as momentum_bt:
        from quant_ai_trader.backtesting.backtester import BacktestResult
        import pandas as pd
        result = BacktestResult(pd.Series([100, 101]), pd.DataFrame(), {"total_return": .01})
        model_bt.return_value = momentum_bt.return_value = result
        metrics = run("QQQ")
    assert metrics["model_promoted"] == 0.0
