"""Non-submitting, fixed-rule SLV ATR-breakout paper-pilot planner."""
from __future__ import annotations
import argparse
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.strategies.breakout import breakout_signals


SLEEVE_NAME = "slv_atr_breakout_v1"

def run() -> dict[str, object]:
    repo = MarketDataRepository(Settings().database_path)
    repo.initialize(); sleeve = repo.get_or_create_capital_sleeve(SLEEVE_NAME, 10_000.0, "SEK")
    bars, spy = repo.load_bars("SLV"), repo.load_bars("SPY")
    if bars.empty or spy.empty: raise ValueError("SLV and SPY history are required")
    signals = breakout_signals(build_feature_dataset(bars, spy_bars=spy))
    latest, bar = signals.iloc[-1], bars.iloc[-1]
    if not bool(latest["entry_signal"]):
        return {"symbol":"SLV", "as_of":str(bars.index[-1].date()), "decision":"NO_TRADE", "reason":"fixed_breakout_entry_not_active", "capital_sleeve":sleeve, "orders_created":False}
    return {"symbol":"SLV", "as_of":str(bars.index[-1].date()), "decision":"PAPER_PLAN_REQUIRES_FX_PRECHECK", "reference_close":float(bar["close"]), "stop_loss_fraction":float(latest["stop_loss_fraction"]), "target_return_fraction":float(latest["target_return_fraction"]), "capital_sleeve":sleeve, "orders_created":False}

if __name__ == "__main__":
    print(run())
