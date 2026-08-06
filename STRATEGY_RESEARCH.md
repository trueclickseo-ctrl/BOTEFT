# Strategy Research Register

This is the permanent decision log for strategy experiments. Record both successful and rejected variants before changing parameters or re-running research. A positive backtest alone never qualifies a strategy for paper trading.

## Status definitions

- **Research only** — backtest was run; not eligible for signals or orders.
- **Rejected** — failed a quality, data, or risk gate; do not retry unchanged.
- **Candidate** — quality gate passed; needs multi-ETF and unseen-period review.
- **Paper approved** — explicitly approved after operator review and reconciliation setup.

## Implemented strategies

| Strategy | Rules | Dataset/result | Status | Decision |
|---|---|---|---|---|
| AI target-before-stop | LightGBM probability; +6% target, -3% stop, 30 sessions; buy probability >=75%, bullish SPY regime | QQQ single-ETF research: total return 10.53%, Sharpe 2.71, 29 trades; ROC-AUC quality gate failed | Rejected | Do not use for paper/live signals. Re-evaluate only with pooled multi-ETF data and a new unseen period. |
| Momentum baseline | Positive 20-day momentum and bullish SPY regime; standard target/stop exits | QQQ: total return 5.24%, Sharpe 0.83 | Research only | Benchmark for AI strategies; not an approved trading strategy. |

## Required evidence for a new candidate

1. Versioned feature and label settings.
2. Purged, date-based walk-forward validation.
3. At least 100 out-of-sample observations, ROC-AUC >= 0.52, and average precision >= 0.05.
4. Comparison against the momentum baseline across multiple ETFs.
5. Data-quality, drift, risk, and reconciliation checks recorded.

## Experiment template

| Date | Strategy/version | Universe | Target/stop/horizon | OOS metrics | Backtest metrics | Outcome | Reason / next action |
|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | | | | | | Candidate / Rejected | |
