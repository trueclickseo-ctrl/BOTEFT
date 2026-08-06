import pandas as pd
from quant_ai_trader.backtesting.evaluation import StrategyEvidenceGate
from quant_ai_trader.strategies.breakout import breakout_signals

def test_breakout_emits_atr_stop_and_evidence_gate_requires_trades():
    index = pd.bdate_range("2024-01-01", periods=210); close = pd.Series(range(100, 310), index=index)
    frame = pd.DataFrame({"adjusted_close": close, "sma_200": close - 1, "atr_14": 2., "spy_trend_50": .01}, index=index)
    assert breakout_signals(frame)["stop_loss_fraction"].dropna().iloc[-1] > 0
    assert StrategyEvidenceGate().evaluate({"number_of_trades": 2})[1] == "insufficient_trade_count"
