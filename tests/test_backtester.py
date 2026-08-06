import pandas as pd

from quant_ai_trader.backtesting.backtester import BacktestConfig, ETFBacktester
from quant_ai_trader.strategies.etf_strategy import StrategyRules, generate_signals
from quant_ai_trader.strategies.baselines import momentum_baseline_signals


def test_signals_require_probability_risk_reward_and_bull_market():
    frame = pd.DataFrame({"buy_probability": [80, 80, 40], "spy_trend_50": [.01, -.01, .01]})
    signals = generate_signals(frame)
    assert signals["entry_signal"].tolist() == [True, False, False]
    assert signals["exit_signal"].tolist() == [False, False, True]


def test_backtester_fills_next_open_and_records_target_exit():
    index = pd.bdate_range("2024-01-01", periods=4)
    bars = pd.DataFrame({
        "open": [100, 100, 100, 100], "high": [101, 101, 106, 101],
        "low": [99, 99, 99, 99], "close": [100, 100, 105, 100],
    }, index=index)
    signals = pd.DataFrame({"entry_signal": [True, False, False, False], "exit_signal": [False] * 4}, index=index)
    result = ETFBacktester(StrategyRules(target_return=.06, stop_loss=.03), BacktestConfig(commission_per_share=0, slippage_bps=0)).run(bars, signals)
    assert len(result.trades) == 1
    assert result.trades.iloc[0]["entry_time"] == index[1]
    assert result.trades.iloc[0]["exit_reason"] == "profit_target"
    assert result.metrics["number_of_trades"] == 1

def test_momentum_baseline_generates_regime_filtered_signals():
    features = pd.DataFrame({"momentum_20": [.1, -.1], "spy_trend_50": [.01, .01]})
    signals = momentum_baseline_signals(features)
    assert signals["entry_signal"].tolist() == [True, False]
