"""Monthly cross-sectional momentum plus low-volatility ETF backtest."""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from quant_ai_trader.backtesting.performance import calculate_performance

@dataclass(frozen=True)
class MomentumLowVolConfig:
    initial_cash: float=100_000.; top_n:int=3; rebalance_days:int=21; trading_cost_bps:float=5.

def run_backtest(frames: dict[str,pd.DataFrame], config: MomentumLowVolConfig=MomentumLowVolConfig()):
    symbols=sorted(frames); dates=sorted(set.intersection(*(set(f.index) for f in frames.values())))
    if len(dates)<config.rebalance_days+2: raise ValueError("Insufficient common history")
    equity,weights,curve,log=config.initial_cash,{},[],[]
    for i,date in enumerate(dates):
        if i: equity*=1+sum(weights.get(s,0)*(frames[s].loc[date,"adjusted_close"]/frames[s].loc[dates[i-1],"adjusted_close"]-1) for s in symbols)
        if i>0 and i%config.rebalance_days==0:
            rows=[]
            for s in symbols:
                row=frames[s].loc[dates[i-1]]
                if pd.notna(row.get("momentum_60")) and pd.notna(row.get("volatility_20")) and row["momentum_60"]>0: rows.append((s,float(row["momentum_60"]),float(row["volatility_20"])))
            scores=pd.DataFrame(rows,columns=["symbol","momentum","volatility"])
            if scores.empty: target={}
            else:
                scores["score"]=.5*scores["momentum"].rank(pct=True)+.5*(-scores["volatility"]).rank(pct=True)
                selected=scores.nlargest(config.top_n,"score")["symbol"].tolist(); target={s:1/len(selected) for s in selected}
            turnover=sum(abs(target.get(s,0)-weights.get(s,0)) for s in set(target)|set(weights)); equity*=1-turnover*config.trading_cost_bps/10_000; weights=target
            log.append({"date":date,"symbols":",".join(target),"turnover":turnover})
        curve.append(equity)
    series=pd.Series(curve,index=dates,name="equity"); return series,pd.DataFrame(log),calculate_performance(series,pd.DataFrame())
