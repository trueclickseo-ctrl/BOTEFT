import numpy as np
import pandas as pd
from quant_ai_trader.backtesting.cross_sectional import CrossSectionalConfig, run_cross_sectional_backtest

def test_cross_sectional_backtest_rebalances_and_produces_equity_curve():
    dates = pd.bdate_range("2024-01-01", periods=70)
    def frame(rate):
        price = 100 * (1 + rate) ** np.arange(70)
        return pd.DataFrame({"adjusted_close": price, "momentum_60": [.1] * 70, "spy_trend_50": [.01] * 70, "spy_return_20": [.01] * 70, "volatility_20": [.2] * 70}, index=dates)
    curve, log, metrics = run_cross_sectional_backtest({"AAA": frame(.001), "BBB": frame(.0001)}, CrossSectionalConfig(rebalance_days=20, top_n=1))
    assert len(log) == 3 and curve.iloc[-1] > curve.iloc[0] and metrics["number_of_trades"] == 0
