"""Structured rotating logs; never include tokens, account keys, or request headers."""
import json, logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"time": self.formatTime(record), "level": record.levelname, "logger": record.name, "message": record.getMessage(), "strategy": getattr(record, "strategy", None), "event": getattr(record, "event", None)})

def configure_logging(directory: Path | str = "logs") -> logging.Logger:
    path = Path(directory); path.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("quant_ai_trader"); logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(path / "quant_ai_trader.jsonl", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
        handler.setFormatter(JsonFormatter()); logger.addHandler(handler)
    return logger
