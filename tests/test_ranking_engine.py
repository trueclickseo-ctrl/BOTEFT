import pandas as pd
from quant_ai_trader.strategies.ranking_engine import rank_etfs

def test_ranking_prefers_relative_strength_with_lower_volatility():
    base = {"spy_trend_50": [.01], "spy_return_20": [.02]}
    qqq = pd.DataFrame(base | {"momentum_60": [.15], "volatility_20": [.2]})
    iwm = pd.DataFrame(base | {"momentum_60": [.08], "volatility_20": [.4]})
    assert rank_etfs({"QQQ": qqq, "IWM": iwm}).iloc[0]["symbol"] == "QQQ"
