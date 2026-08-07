"""Versioned cross-sectional ML research; diagnostics only, never an order model."""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
from uuid import uuid4
import pandas as pd
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.models.train_model import train_target_stop_model
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE


def build_dataset(repo: MarketDataRepository, symbols: list[str], horizon: int = 20) -> pd.DataFrame:
    spy = repo.load_bars("SPY"); frames=[]
    for symbol in symbols:
        frame=build_feature_dataset(repo.load_bars(symbol.upper()),spy_bars=spy).copy()
        frame["forward_return"] = frame["adjusted_close"].shift(-horizon)/frame["adjusted_close"]-1
        frame.index=pd.MultiIndex.from_arrays([frame.index,[symbol.upper()]*len(frame)],names=["date","symbol"]); frames.append(frame)
    dataset=pd.concat(frames).sort_index()
    median=dataset.groupby(level="date")["forward_return"].transform("median")
    dataset["target_hit_before_stop"]=(dataset["forward_return"]>median).astype(float)
    dataset.loc[dataset["forward_return"].isna(),"target_hit_before_stop"]=float("nan")
    return dataset


def run(symbols: list[str]) -> dict[str,float]:
    repo=MarketDataRepository(Settings().database_path); repo.initialize()
    dataset=build_dataset(repo,symbols)
    result=train_target_stop_model(dataset,target_return=.0,stop_loss=.01,holding_period_days=20)
    metrics=result.artifact.validation_metrics | {"research_only":1.0,"universe_size":float(len(symbols))}
    repo.record_strategy_run(str(uuid4()),"ai_cross_sectional_outperformance_v1",",".join(symbols).upper(),datetime.now(UTC).isoformat(),metrics)
    return metrics

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--symbols",nargs="+",default=list(DEFAULT_UNIVERSE)); args=parser.parse_args(); print(run(args.symbols))
