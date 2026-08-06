import numpy as np
import pandas as pd
from quant_ai_trader.backtesting.dual_momentum import RiskTargetedDualMomentumConfig, run_risk_targeted_dual_momentum_backtest


def test_risk_targeted_dual_momentum_is_unlevered():
    dates = pd.bdate_range("2023-01-02", periods=80)
    rising = 100 * (1 + np.sin(np.arange(80)) * .02 + .002) .cumprod()
    falling = 100 * (.999 ** np.arange(80))
    frames = {"UP": pd.DataFrame({"adjusted_close": rising}, index=dates), "DOWN": pd.DataFrame({"adjusted_close": falling}, index=dates)}
    _, decisions, metrics = run_risk_targeted_dual_momentum_backtest(frames, RiskTargetedDualMomentumConfig(lookback_days=20, volatility_lookback_days=10, rebalance_days=10))
    assert decisions["exposure"].between(0, 1).all() and metrics["average_exposure"] <= 1
