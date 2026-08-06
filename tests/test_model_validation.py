from quant_ai_trader.models.model_manager import ModelArtifact
from quant_ai_trader.models.model_validation import ModelQualityGate

def test_model_quality_gate_rejects_weak_and_approves_validated_models():
    weak = ModelArtifact.create(None, [], .06, .03, 30, {"roc_auc": .5, "average_precision": .1, "oos_observations": 200})
    assert ModelQualityGate().validate(weak) == (False, "roc_auc_below_threshold")
    strong = ModelArtifact.create(None, [], .06, .03, 30, {"roc_auc": .6, "average_precision": .1, "oos_observations": 200})
    assert ModelQualityGate().validate(strong) == (True, "approved")
