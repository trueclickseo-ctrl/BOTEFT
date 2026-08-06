"""Versioned persistence for model artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib


@dataclass
class ModelArtifact:
    model: Any
    feature_columns: list[str]
    target_return: float
    stop_loss: float
    holding_period_days: int
    trained_at: str
    validation_metrics: dict[str, float]
    feature_statistics: dict[str, dict[str, float]] | None = None

    @classmethod
    def create(cls, model: Any, feature_columns: list[str], target_return: float, stop_loss: float, holding_period_days: int, validation_metrics: dict[str, float], feature_statistics: dict[str, dict[str, float]] | None = None) -> "ModelArtifact":
        return cls(model, feature_columns, target_return, stop_loss, holding_period_days, datetime.now(UTC).isoformat(), validation_metrics, feature_statistics)

    def metadata(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("model")
        return data


class ModelManager:
    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)

    def save(self, artifact: ModelArtifact, name: str = "target_stop_lgbm") -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{name}.joblib"
        joblib.dump(artifact, path)
        return path

    def load(self, name: str = "target_stop_lgbm") -> ModelArtifact:
        path = self.directory / f"{name}.joblib"
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found: {path}")
        return joblib.load(path)
