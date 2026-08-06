"""Lightweight feature-distribution drift monitoring for deployed model artifacts."""
from dataclasses import dataclass
import pandas as pd
from quant_ai_trader.models.model_manager import ModelArtifact

@dataclass(frozen=True)
class DriftReport:
    drifted: bool
    feature_shifts: dict[str, float]

def detect_feature_drift(artifact: ModelArtifact, features: pd.DataFrame, threshold: float = 3.0) -> DriftReport:
    baseline = artifact.feature_statistics or {}
    shifts: dict[str, float] = {}
    for column, stats in baseline.items():
        if column not in features or not stats.get("std"): continue
        shift = abs(float(features[column].dropna().mean()) - stats["mean"]) / stats["std"]
        if shift >= threshold: shifts[column] = shift
    return DriftReport(bool(shifts), shifts)
