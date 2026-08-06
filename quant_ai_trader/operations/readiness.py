"""Consolidated system state for operators and deployment checks."""
from dataclasses import dataclass
from pathlib import Path
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.models.model_manager import ModelManager
from quant_ai_trader.models.model_validation import ModelQualityGate

@dataclass(frozen=True)
class ReadinessReport:
    ready_for_research: bool
    ready_for_paper: bool
    ready_for_live: bool
    checks: dict[str, bool]

def assess_readiness(repository: MarketDataRepository, manager: ModelManager, kill_switch_file: Path | str = "runtime/KILL_SWITCH") -> ReadinessReport:
    checks = {"market_data_available": bool(repository.list_symbols()), "model_available": False, "model_quality_approved": False, "kill_switch_inactive": not Path(kill_switch_file).exists()}
    try:
        artifact = manager.load(); checks["model_available"] = True
        checks["model_quality_approved"] = ModelQualityGate().validate(artifact)[0]
    except FileNotFoundError: pass
    research = checks["market_data_available"]
    paper = research and checks["model_quality_approved"] and checks["kill_switch_inactive"]
    # Live remains operator-gated beyond software readiness.
    return ReadinessReport(research, paper, False, checks)
