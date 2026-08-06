from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.models.model_manager import ModelManager
from quant_ai_trader.operations.readiness import assess_readiness

def test_readiness_requires_data_model_and_inactive_kill_switch(tmp_path, sample_bars):
    repo = MarketDataRepository(tmp_path / "db.sqlite"); repo.initialize()
    manager = ModelManager(tmp_path / "models")
    assert not assess_readiness(repo, manager, tmp_path / "KILL_SWITCH").ready_for_research
    repo.upsert_bars("SPY", sample_bars)
    report = assess_readiness(repo, manager, tmp_path / "KILL_SWITCH")
    assert report.ready_for_research and not report.ready_for_paper
