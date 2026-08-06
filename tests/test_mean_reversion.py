import pandas as pd
from quant_ai_trader.strategies.mean_reversion import rsi_mean_reversion_signals

def test_mean_reversion_buys_only_bullish_rsi_pullback():
    frame = pd.DataFrame({"adjusted_close": [110, 90], "sma_200": [100, 100], "rsi_14": [30, 30], "spy_trend_50": [.01, .01]})
    assert rsi_mean_reversion_signals(frame)["entry_signal"].tolist() == [True, False]
