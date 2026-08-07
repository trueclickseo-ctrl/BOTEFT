# BOTEF Stock Research and Test Record

This file is the stock-only technical evidence log. ETF research remains in
`STRATEGY_RESEARCH.md`; no ETF result is used to approve a stock strategy.

## Approval rules

- Minimum net Sharpe: 0.75
- Maximum drawdown: -15.00%
- At least three of four positive chronological folds
- Positive return under doubled Saxo commission, FX, and slippage assumptions
- Historical and bootstrap results are rejection evidence only. They cannot
  authorize paper or live orders.

## Data boundaries

- Prices are Yahoo adjusted-close research data stored separately under
  `data/stocks/`; generated SQLite databases are excluded from Git.
- Adjusted close includes gross distribution adjustments, but investor-specific
  dividend withholding tax is not modeled.
- Large universes use membership frozen on 2026-08-07 and projected backward.
  This creates survivorship/look-ahead bias and prevents approval.
- SPY is a regime benchmark only and is not a stock candidate.

## Completed tests

| Candidate | Universe | Net return | Sharpe | Max drawdown | Positive folds | Doubled-cost return | Historical gate |
|---|---:|---:|---:|---:|---:|---:|---|
| `stock_core_satellite_consolidated_v1` | Current DJIA 30 | +213.74% | 1.209 | -12.76% | 3/4 | +184.77% | Numerical pass; research-only |
| `stock_literature_momentum_v1` | Current Nasdaq-100 (101 securities) | +217.43% | 1.011 | -18.69% | 3/4 | +184.89% | Rejected: drawdown |
| `stock_literature_momentum_v1` | Current S&P 500 Top 50 | +136.47% | 0.800 | -15.11% | 3/4 | +108.86% | Rejected: drawdown |

## Dependent-return robustness test

The next frozen test uses a 2,000-sample Politis-Romano stationary bootstrap
with a 20-session expected block length. It resamples the canonical net-of-cost
daily portfolio return series, preserving short-run dependence and volatility
clustering better than IID shuffling. A candidate must have at least 95%
bootstrap probability of jointly clearing Sharpe 0.75, drawdown -15%, and
positive total return. The test is rejection-only and performs no parameter
tuning.

### Results (2026-08-07)

| Candidate | Sharpe 5th pct | Drawdown 5th pct | Sharpe pass probability | Drawdown pass probability | Joint pass probability | Decision |
|---|---:|---:|---:|---:|---:|---|
| DJIA-30 core-satellite | 0.788 | -18.87% | 96.40% | 82.90% | 81.30% | Failed 95% robustness gate |
| Nasdaq-100 momentum | 0.542 | -24.60% | 81.80% | 42.45% | 40.35% | Failed 95% robustness gate |
| S&P Top-50 momentum | 0.394 | -23.79% | 60.80% | 52.05% | 40.85% | Failed 95% robustness gate |

All 2,000 bootstrap paths for each candidate used the same frozen rules and
canonical cost engine. Total-return fifth percentiles remained positive
(+111.37%, +81.62%, and +48.85%, respectively), so profitability is not the
dominant weakness. Drawdown uncertainty is the decisive blocker. The strongest
candidate is still the DJIA-30 core-satellite, but its 81.30% joint probability
is materially below the preregistered 95% requirement.

## Current execution status

No stock strategy is approved for paper or live execution. The bootstrap test
did not promote any candidate. The central strategy
registry remains fail-closed. Approval additionally requires point-in-time
universe evidence, share rounding, Saxo instrument/UIC checks, broker prechecks,
and preregistered forward validation.

## Signal publication layer

The stock engine now publishes a separate market decision and execution status.
`BUY`, `HOLD`, `ROTATE`, `EXIT`, and `CASH` describe what the frozen signal says
for the current tactical sleeve. They do not imply statistical approval or
broker authorization. The output includes the selected symbol, target weight,
momentum, signal/rebalance dates, whole-share target when account equity is
provided, Saxo mapping state, and explicit submission blockers. It is exposed
read-only at `/stocks/decision` and on the dashboard.

On 2026-08-07 the raw strategy output was `BUY CAT` at a 10% tactical
target. The signal used the 2026-07-15 close, rebalanced on 2026-07-16, and
scheduled its next 21-business-session review for 2026-08-14. Saxo SIM
read-only validation resolved `CAT:xnys` as Stock UIC 305. No precheck or order
submission endpoint was called.

The publication bug that exposed a raw ranking as an authorized `BUY` was
removed. Unless every execution gate passes, the dashboard now displays
`CANDIDATE CAT — NOT ACTIONABLE` and separately reports raw signal `BUY`.
Read-only Saxo reconciliation normalizes exchange-suffixed symbols, compares
only BOTEF's managed stock universe, reports external positions without taking
ownership of them, and treats a missing local ledger as flat only when Saxo
independently confirms there are no managed positions.

The first live read-only reconciliation found pre-existing Saxo SIM positions
in UNH and V plus five symbols outside BOTEF's stock universe. Because BOTEF did
not create them, UNH and V were captured as an external quantity baseline
rather than silently adopted. The subsequent reconciliation passed with no
BOTEF-managed differences. The SIM kill switch was independently verified
inactive. The local baseline lives under ignored runtime state and is not shared
through Git.
