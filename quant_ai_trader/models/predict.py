"""Inference helpers for the target-before-stop model."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_ai_trader.models.model_manager import ModelArtifact


@dataclass(frozen=True)
class OpportunityPrediction:
    buy_probability: float
    expected_return: float
    target_return: float
    stop_loss: float
    decision: str


def predict_opportunity(artifact: ModelArtifact, features: pd.DataFrame, buy_threshold: float = 0.75) -> OpportunityPrediction:
    """Predict the most recent row; output is a research signal, not an order."""
    missing = set(artifact.feature_columns) - set(features.columns)
    if missing:
        raise ValueError(f"Features missing from prediction input: {sorted(missing)}")
    row = features.loc[:, artifact.feature_columns].tail(1)
    if row.empty or row.isna().any(axis=None):
        raise ValueError("Latest feature row is empty or incomplete")
    probability = float(artifact.model.predict_proba(row)[0, 1])
    expected_return = probability * artifact.target_return - (1 - probability) * artifact.stop_loss
    return OpportunityPrediction(
        buy_probability=probability * 100,
        expected_return=expected_return * 100,
        target_return=artifact.target_return * 100,
        stop_loss=artifact.stop_loss * 100,
        decision="BUY" if probability >= buy_threshold else "NO_TRADE",
    )


def predict_probabilities(artifact: ModelArtifact, features: pd.DataFrame) -> pd.Series:
    """Return model probabilities for complete historical feature rows."""
    missing = set(artifact.feature_columns) - set(features.columns)
    if missing:
        raise ValueError(f"Features missing from prediction input: {sorted(missing)}")
    complete = features.loc[:, artifact.feature_columns].dropna()
    probabilities = artifact.model.predict_proba(complete)[:, 1] * 100
    return pd.Series(probabilities, index=complete.index, name="buy_probability")
