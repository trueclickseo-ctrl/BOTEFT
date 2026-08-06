"""Promotion gates that prevent unvalidated research models from being deployed."""
from dataclasses import dataclass
from quant_ai_trader.models.model_manager import ModelArtifact

@dataclass(frozen=True)
class ModelQualityGate:
    minimum_roc_auc: float = .52
    minimum_average_precision: float = .05
    minimum_oos_observations: int = 100

    def validate(self, artifact: ModelArtifact) -> tuple[bool, str]:
        metrics = artifact.validation_metrics
        if metrics.get("oos_observations", 0) < self.minimum_oos_observations: return False, "insufficient_oos_observations"
        if metrics.get("roc_auc", 0) < self.minimum_roc_auc: return False, "roc_auc_below_threshold"
        if metrics.get("average_precision", 0) < self.minimum_average_precision: return False, "average_precision_below_threshold"
        return True, "approved"
