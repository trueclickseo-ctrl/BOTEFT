"""Central configuration for the quantitative research framework."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv


DEFAULT_ETF_UNIVERSE = (
    "SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
    "XLP", "TLT", "GLD", "SLV",
)


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Paths are resolved relative to the repository root."""

    database_path: Path = Path("data/quant_ai_trader.sqlite3")
    etf_universe: tuple[str, ...] = field(default_factory=lambda: DEFAULT_ETF_UNIVERSE)
    trading_days_per_year: int = 252
    min_history_days: int = 252
    outlier_zscore_threshold: float = 8.0
    target_return: float = 0.06
    stop_loss: float = 0.03
    holding_period_days: int = 30
    buy_probability_threshold: float = 0.75
    exit_probability_threshold: float = 0.45
    model_directory: Path = Path("artifacts/models")

    def __post_init__(self) -> None:
        object.__setattr__(self, "database_path", Path(self.database_path))
        object.__setattr__(self, "model_directory", Path(self.model_directory))


@dataclass(frozen=True)
class SaxoSettings:
    """Saxo OpenAPI connection settings sourced from environment variables only."""

    access_token: str
    environment: str = "sim"
    instruments: dict[str, dict[str, str | int]] = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        environments = {
            "sim": "https://gateway.saxobank.com/sim/openapi",
            "live": "https://gateway.saxobank.com/openapi",
        }
        try:
            return environments[self.environment]
        except KeyError as error:
            raise ValueError("SAXO_ENVIRONMENT must be either 'sim' or 'live'") from error

    @classmethod
    def from_environment(cls) -> "SaxoSettings":
        load_dotenv()
        token = os.getenv("SAXO_ACCESS_TOKEN")
        if not token:
            raise RuntimeError("SAXO_ACCESS_TOKEN is required; do not place broker credentials in source code.")
        raw_instruments = os.getenv("SAXO_INSTRUMENTS_JSON", "{}")
        try:
            instruments = json.loads(raw_instruments)
        except json.JSONDecodeError as error:
            raise ValueError("SAXO_INSTRUMENTS_JSON must be valid JSON") from error
        if not isinstance(instruments, dict):
            raise ValueError("SAXO_INSTRUMENTS_JSON must be a JSON object keyed by symbol")
        return cls(token, os.getenv("SAXO_ENVIRONMENT", "sim").lower(), instruments)
