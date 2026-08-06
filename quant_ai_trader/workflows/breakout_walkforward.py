"""Rolling unseen-window validation for fixed breakout rules."""
import argparse
import pandas as pd
from quant_ai_trader.backtesting.backtester import ETFBacktester
from quant_ai_trader.backtesting.evaluation import StrategyEvidenceGate
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.strategies.breakout import breakout_signals

def run(symbol: str, folds: int = 4) -> dict[str, float]:
    repo = MarketDataRepository(Settings().database_path); bars, spy = repo.load_bars(symbol), repo.load_bars("SPY")
    signals = breakout_signals(build_feature_dataset(bars, spy_bars=spy)); start = int(len(bars) * .40); window = (len(bars) - start) // folds
    results = []
    for fold in range(folds):
        left, right = start + fold * window, start + (fold + 1) * window if fold < folds - 1 else len(bars)
        results.append(ETFBacktester().run(bars.iloc[left:right], signals.iloc[left:right]).metrics)
    summary = {"folds": float(folds), "average_sharpe": float(pd.Series([r["sharpe_ratio"] for r in results]).mean()), "total_trades": float(sum(r["number_of_trades"] for r in results)), "worst_drawdown": float(min(r["maximum_drawdown"] for r in results))}
    summary["evidence"] = StrategyEvidenceGate().evaluate({"number_of_trades": summary["total_trades"], "sharpe_ratio": summary["average_sharpe"], "maximum_drawdown": summary["worst_drawdown"]})[1]
    return summary
if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--symbol", required=True)
    print(run(parser.parse_args().symbol))
