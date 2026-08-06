import pandas as pd
from quant_ai_trader.models.drift import detect_feature_drift
from quant_ai_trader.models.model_manager import ModelArtifact

def test_feature_drift_detects_large_standardized_shift():
    artifact = ModelArtifact.create(None, ["rsi"], .06, .03, 30, {}, {"rsi": {"mean": 50.0, "std": 10.0}})
    assert not detect_feature_drift(artifact, pd.DataFrame({"rsi": [55, 56]})).drifted
    report = detect_feature_drift(artifact, pd.DataFrame({"rsi": [90, 91]}))
    assert report.drifted and "rsi" in report.feature_shifts
