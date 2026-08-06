"""Compare the fixed ATR-breakout strategy with passive exposure across ETFs.

This research workflow records both runs but never creates an order or changes
strategy parameters. A local candidate remains research-only until its separate
holdout and walk-forward evidence gates are satisfied.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from quant_ai_trader.workflows.breakout import run as run_breakout
from quant_ai_trader.workflows.buy_and_hold import run as run_buy_and_hold


DEFAULT_UNIVERSE = (
    "SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "TLT", "GLD", "SLV",
)


def _verdict(active: dict[str, float], benchmark: dict[str, float]) -> str:
    """Return a conservative relative-research classification."""
    active_is_candidate = active.get("evidence") == "candidate"
    outperforms = (
        active.get("total_return", 0.0) > benchmark.get("total_return", 0.0)
        and active.get("sharpe_ratio", 0.0) > benchmark.get("sharpe_ratio", 0.0)
    )
    if active_is_candidate and outperforms:
        return "research_candidate_beats_benchmark"
    if active_is_candidate:
        return "candidate_does_not_beat_benchmark"
    if outperforms:
        return "insufficient_evidence_despite_benchmark_outperformance"
    return "does_not_beat_benchmark"


def run(symbols: Sequence[str] = DEFAULT_UNIVERSE) -> dict[str, object]:
    """Run unchanged breakout and passive benchmarks for every supplied ETF."""
    results: list[dict[str, object]] = []
    for raw_symbol in symbols:
        symbol = raw_symbol.upper()
        breakout = run_breakout(symbol)
        benchmark = run_buy_and_hold(symbol)
        results.append(
            {
                "symbol": symbol,
                "breakout_total_return": breakout["total_return"],
                "benchmark_total_return": benchmark["total_return"],
                "breakout_sharpe": breakout["sharpe_ratio"],
                "benchmark_sharpe": benchmark["sharpe_ratio"],
                "breakout_maximum_drawdown": breakout["maximum_drawdown"],
                "benchmark_maximum_drawdown": benchmark["maximum_drawdown"],
                "breakout_trades": breakout["number_of_trades"],
                "evidence": breakout["evidence"],
                "verdict": _verdict(breakout, benchmark),
            }
        )
    candidates = sum(row["verdict"] == "research_candidate_beats_benchmark" for row in results)
    return {
        "strategy": "atr_breakout_v1",
        "universe_size": len(results),
        "research_candidates": candidates,
        "paper_trading_approved": False,
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_UNIVERSE))
    print(run(parser.parse_args().symbols))
