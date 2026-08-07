"""Non-submitting, fixed-rule SLV ATR-breakout paper-pilot planner."""
from __future__ import annotations
import argparse
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.risk.position_sizing import calculate_position_size
from quant_ai_trader.strategies.breakout import breakout_signals


def run(account_equity: float = 100_000.0) -> dict[str, object]:
    repo = MarketDataRepository(Settings().database_path)
    bars, spy = repo.load_bars("SLV"), repo.load_bars("SPY")
    if bars.empty or spy.empty: raise ValueError("SLV and SPY history are required")
    signals = breakout_signals(build_feature_dataset(bars, spy_bars=spy))
    latest, bar = signals.iloc[-1], bars.iloc[-1]
    if not bool(latest["entry_signal"]):
        return {"symbol":"SLV", "as_of":str(bars.index[-1].date()), "decision":"NO_TRADE", "reason":"fixed_breakout_entry_not_active", "orders_created":False}
    reference_price=float(bar["close"])
    size=calculate_position_size(account_equity,reference_price,float(latest["stop_loss_fraction"]),float(latest["target_return_fraction"]))
    return {"symbol":"SLV", "as_of":str(bars.index[-1].date()), "decision":"PAPER_PLAN_REQUIRES_PREFLIGHT", "reference_close":reference_price, "shares":size.shares, "notional":size.notional, "stop_price":size.stop_price, "target_price":size.target_price, "orders_created":False}

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--account-equity",type=float,default=100_000.0); args=parser.parse_args(); print(run(args.account_equity))
