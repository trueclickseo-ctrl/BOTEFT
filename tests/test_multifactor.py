import pandas as pd
from quant_ai_trader.strategies.multifactor import multifactor_trend_signals

def test_multifactor_requires_all_confirmations():
    frame = pd.DataFrame({"adjusted_close":[110],"sma_50":[105],"sma_200":[100],"momentum_60":[.1],"macd_histogram":[.2],"rsi_14":[55],"atr_14":[2],"spy_trend_50":[.01]})
    assert multifactor_trend_signals(frame)["entry_signal"].iloc[0]
