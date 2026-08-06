import pandas as pd
from quant_ai_trader.strategies.trend_following import trend_following_signals

def test_trend_following_requires_confirmed_trend_and_regime():
    frame = pd.DataFrame({"adjusted_close": [110, 90], "sma_50": [100, 100], "sma_200": [90, 90], "momentum_60": [.1, .1], "spy_trend_50": [.01, .01]})
    assert trend_following_signals(frame)["entry_signal"].tolist() == [True, False]
