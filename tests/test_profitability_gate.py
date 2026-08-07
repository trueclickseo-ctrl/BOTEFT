from quant_ai_trader.backtesting.backtester import BacktestConfig, ETFBacktester
from quant_ai_trader.backtesting.evaluation import ProfitabilityGate
from quant_ai_trader.strategies.etf_strategy import StrategyRules


def test_saxo_cost_model_applies_minimum_commission_and_fx(sample_bars):
    signals = __import__("pandas").DataFrame(False, index=sample_bars.index, columns=["entry_signal", "exit_signal"])
    signals.iloc[0, signals.columns.get_loc("entry_signal")] = True
    signals.iloc[2, signals.columns.get_loc("exit_signal")] = True
    result = ETFBacktester(StrategyRules(), BacktestConfig.saxo_us_etf_eur()).run(sample_bars, signals)
    trade = result.trades.iloc[0]
    assert trade["entry_commission"] >= 1
    assert trade["exit_commission"] >= 1
    assert trade["entry_fx_cost"] > 0 and trade["total_cost"] > 2


def test_profitability_gate_requires_repeatable_stress_resistant_profit():
    metrics = {"number_of_trades": 40, "total_return": .10, "average_net_profit": 5,
               "profit_factor": 1.4, "sharpe_ratio": .9, "maximum_drawdown": -.10}
    assert ProfitabilityGate().evaluate(metrics, fold_wins=3, stress_total_return=.03)[0]
    approved, blockers = ProfitabilityGate().evaluate(metrics, fold_wins=2, stress_total_return=-.01)
    assert not approved and "fails_doubled_cost_stress" in blockers
