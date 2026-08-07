# Stock Strategy Research Register

This is the permanent decision log for stock-only experiments. It is isolated from ETF research, data, workflows, and candidate selection. A numerical pass never authorizes paper orders.

## Frozen boundaries

- Workflow package: `quant_ai_trader.workflows.stocks`
- Strategy package: `quant_ai_trader.strategies.stocks`
- Research database: `data/stocks/us_adjusted.sqlite3`
- Universe: 30 current DJIA constituents frozen on 2026-08-07
- Benchmark: SPY for regime features only; SPY is not a stock candidate
- Forward freeze date: 2026-08-08
- Approval: centrally fail-closed in `strategy_approval.py`

## Research results

| Date | Strategy/version | Rules and universe | Evidence | Status | Decision |
|---|---|---|---|---|---|
| 2026-08-07 | Frozen US blue-chip screen | Thirty current DJIA blue chips; 150 single-stock cases and seven portfolio families; unchanged Saxo EUR-account costs and gates | 157 evaluations, 21 net-positive, no single-stock pass. Two preliminary portfolio passes required architecture review; the ETF-sector diversified result was invalid because all stocks were classified as `Unclassified`. | Screen complete | Only the core-satellite candidate proceeded to canonical validation. |
| 2026-08-07 | `stock_core_satellite_consolidated_v1` | 50% volatility-matched equal-weight stock core plus 50% risk-targeted dual momentum; consolidated by symbol; 10% hard stock cap; excess cash; canonical exact costs | +213.74% return, 1.209 Sharpe, -12.76% drawdown, 3/4 positive folds, +184.77% doubled-cost return, 1.53x annual turnover, 47.11% average invested weight. Cap bound on 2,576 sessions. | Research-only numerical pass | Survivorship bias, same-sample selection, gross-dividend adjustment, Saxo tradability, share rounding, broker prechecks, and forward validation remain unresolved. Paper orders stay blocked. |
| 2026-08-07 | `stock_literature_momentum_v1` expanded universes | Preregistered 12-1 momentum, monthly top-five selection, SPY/200-day regime, inverse-volatility sizing, 10% stock cap and exact costs; tested separately on 101 Nasdaq-100 securities and S&P 500 Top 50 | Nasdaq-100: +217.43%, 1.011 Sharpe, -18.69% drawdown, 3/4 folds, +184.89% stress. S&P Top 50: +136.47%, 0.800 Sharpe, -15.11% drawdown, 3/4 folds, +108.86% stress. | Rejected | Both violate the fixed -15% drawdown gate. Do not tune the threshold or substitute constituents after results. Current membership projected backward also creates survivorship bias. |

## Data and statistical limitations

- Current constituents projected backward create survivorship bias.
- Yahoo adjusted history is an unofficial personal-use research source.
- Adjusted close does not model investor-specific US dividend withholding tax.
- Whole-share execution, stock UICs, corporate-action handling, and broker prechecks are not yet validated.
- Historical statistics may reject this candidate but cannot approve it; only preregistered forward evidence may change its status.
