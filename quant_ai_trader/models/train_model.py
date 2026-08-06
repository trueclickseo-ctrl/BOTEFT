"""Walk-forward LightGBM training without temporal leakage."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit

from quant_ai_trader.features.feature_pipeline import model_feature_columns
from quant_ai_trader.models.model_manager import ModelArtifact


@dataclass(frozen=True)
class TrainingResult:
    artifact: ModelArtifact
    out_of_sample_predictions: pd.Series


def train_target_stop_model(
    dataset: pd.DataFrame,
    target_return: float = 0.06,
    stop_loss: float = 0.03,
    holding_period_days: int = 30,
    n_splits: int = 5,
) -> TrainingResult:
    """Evaluate then fit a binary target-before-stop model using chronological folds.

    The holding period is used as the splitter's gap, purging observations whose
    outcomes overlap the start of each validation window.
    """
    label = "target_hit_before_stop"
    if label not in dataset:
        raise ValueError(f"Dataset must include {label}; call create_target_stop_labels first")
    columns = model_feature_columns(dataset)
    eligible = dataset.dropna(subset=columns + [label]).copy().sort_index()
    if eligible[label].nunique() < 2:
        raise ValueError("Training data must contain both target-hit and non-target-hit outcomes")
    if len(eligible) < max(100, (n_splits + 1) * 20):
        raise ValueError("Insufficient labelled observations for walk-forward validation")
    if len(eligible) <= holding_period_days + n_splits + 1:
        raise ValueError("Insufficient rows after applying the holding-period purge gap")

    x = eligible[columns]
    y = eligible[label].astype(int)
    splitter = TimeSeriesSplit(n_splits=n_splits, gap=holding_period_days)
    oos = pd.Series(np.nan, index=eligible.index, name="target_hit_probability")
    for train_indices, validation_indices in splitter.split(x):
        model = _make_model()
        model.fit(x.iloc[train_indices], y.iloc[train_indices])
        oos.iloc[validation_indices] = model.predict_proba(x.iloc[validation_indices])[:, 1]

    observed = oos.notna()
    if y.loc[observed].nunique() < 2:
        raise ValueError("Walk-forward validation contains only one class")
    metrics = {
        "roc_auc": float(roc_auc_score(y.loc[observed], oos.loc[observed])),
        "average_precision": float(average_precision_score(y.loc[observed], oos.loc[observed])),
        "brier_score": float(brier_score_loss(y.loc[observed], oos.loc[observed])),
        "oos_observations": float(observed.sum()),
    }
    final_model = _make_model()
    final_model.fit(x, y)
    statistics = {column: {"mean": float(x[column].mean()), "std": float(x[column].std(ddof=0))} for column in columns}
    artifact = ModelArtifact.create(final_model, columns, target_return, stop_loss, holding_period_days, metrics, statistics)
    return TrainingResult(artifact, oos)


def _make_model():
    try:
        from lightgbm import LGBMClassifier
    except ImportError as error:
        raise RuntimeError("LightGBM is required. Install dependencies from requirements.txt.") from error
    return LGBMClassifier(
        objective="binary", n_estimators=300, learning_rate=0.03, num_leaves=15,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, random_state=42,
        n_jobs=-1, verbosity=-1,
    )
