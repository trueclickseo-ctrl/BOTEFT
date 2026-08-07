import numpy as np
import pandas as pd
from quant_ai_trader.strategies.stocks.literature_momentum import LiteratureMomentumConfig, build_literature_momentum_weights


def test_literature_momentum_is_capped_and_lagged():
    dates=pd.bdate_range("2020-01-01",periods=330); x=np.arange(330)
    prices=pd.DataFrame({f"S{i}":100*np.exp((.0002+i*.0001)*x+.01*np.sin(x/(7+i))) for i in range(6)},index=dates)
    benchmark=pd.Series(100*np.exp(.0004*x+.005*np.sin(x/9)),index=dates)
    config=LiteratureMomentumConfig()
    weights=build_literature_momentum_weights(prices,benchmark,config)
    assert weights.max().max() <= .10+1e-12
    assert weights.sum(axis=1).max() <= .50+1e-12
    assert prices.index.get_loc(weights.sum(axis=1).ne(0).idxmax()) > config.lookback_days+config.skip_recent_days
