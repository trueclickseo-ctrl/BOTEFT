"""Evaluate a monthly, cash-aware dual-momentum ETF rotation strategy."""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
from uuid import uuid4
from quant_ai_trader.backtesting.dual_momentum import run_dual_momentum_backtest, run_equal_weight_backtest
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE


def run(symbols: list[str]) -> dict[str, float]:
    repo = MarketDataRepository(Settings().database_path); repo.initialize()
    normalized = [symbol.upper() for symbol in symbols]
    frames = {symbol: repo.load_bars(symbol) for symbol in normalized}
    missing = [symbol for symbol, frame in frames.items() if frame.empty]
    if missing: raise ValueError(f"Missing stored bars for: {', '.join(missing)}")
    _, decisions, metrics = run_dual_momentum_backtest(frames)
    _, benchmark = run_equal_weight_backtest(frames)
    metrics["unique_holdings"] = float(decisions["holding"].nunique()) if not decisions.empty else 0.0
    metrics["equal_weight_total_return"] = benchmark["total_return"]
    metrics["equal_weight_sharpe"] = benchmark["sharpe_ratio"]
    metrics["equal_weight_maximum_drawdown"] = benchmark["maximum_drawdown"]
    metrics["risk_gate_passed"] = float(metrics["maximum_drawdown"] >= -.20)
    metrics["beats_equal_weight"] = float(
        metrics["risk_gate_passed"] and metrics["total_return"] > benchmark["total_return"] and metrics["sharpe_ratio"] > benchmark["sharpe_ratio"]
    )
    metrics["research_only"] = 1.0
    repo.record_strategy_run(str(uuid4()), "dual_momentum_rotation_v1", ",".join(normalized), datetime.now(UTC).isoformat(), metrics)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_UNIVERSE))
    print(run(parser.parse_args().symbols))
