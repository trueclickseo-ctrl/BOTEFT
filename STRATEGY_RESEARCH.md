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
| AI target-before-stop, pooled v1 | Same model/rules; pooled QQQ, IWM, XLK, XLF; date-level purged walk-forward validation | ROC-AUC 0.5062, average precision 0.3546, Brier 0.3010, 4,053 OOS observations; average backtest return 2.87% | Rejected | Do not rerun unchanged. Feature/label design must change because discrimination is effectively random and fails the 0.52 ROC-AUC gate. |
| Momentum baseline | Positive 20-day momentum and bullish SPY regime; standard target/stop exits | QQQ: total return 5.24%, Sharpe 0.83 | Research only | Benchmark for AI strategies; not an approved trading strategy. |
| Regime-aware cross-sectional ranking v1 | Rank ETFs by 60-day momentum, SPY-relative strength, and volatility penalty; only when SPY trend is positive | QQQ/IWM/XLK/XLF: total return 3.50%, annual return 0.73%, Sharpe 0.12, maximum drawdown -36.97% | Rejected | Do not rerun unchanged. The risk-adjusted result is unacceptable; redesign allocation and exit rules before further evaluation. |
| Regime-aware cross-sectional ranking v2 defensive | v1 ranking plus daily move-to-cash when SPY 50-day trend is non-positive | QQQ/IWM/XLK/XLF: total return 21.66%, annual return 4.21%, Sharpe 0.43, maximum drawdown -31.79% | Rejected | Do not rerun unchanged. Return improved but drawdown and risk-adjusted performance remain unacceptable. |
| Trend-following v1 | Close above SMA50, SMA50 above SMA200, positive 60-day momentum, bullish SPY; exit below SMA50/risk-off | QQQ/IWM/XLK/XLF: average total return 1.69%, average Sharpe 0.28; IWM return -0.68%, Sharpe -0.12 | Rejected | Do not rerun unchanged. Drawdowns were controlled, but returns and cross-ETF consistency are inadequate. |
| RSI mean-reversion v1 | Buy RSI14 <35 only above SMA200 in bullish SPY regime; exit RSI >55 or trend break | QQQ/IWM/XLK/XLF: five trades total; QQQ Sharpe 0.56 but IWM Sharpe -0.14; 1–2 trades per ETF | Rejected | Do not rerun unchanged. Trade count is far too small for statistical confidence; perfect win rates are one-trade artifacts. |
| ATR breakout v1 | 55-day breakout above SMA200 in bullish SPY regime; 20-day exit; 2x ATR stop and 2R target | QQQ: return 5.51%, Sharpe 0.96, drawdown -1.00%, 39 trades. IWM return -1.92%, Sharpe -0.46; XLK Sharpe 0.37; XLF only 23 trades | Rejected for universe-wide promotion | QQQ-specific candidate only. Do not paper trade until a revised cross-ETF or asset-specific mandate is validated. |
| ATR breakout v1 QQQ holdout | Same fixed rules, final 30% of QQQ history held out from aggregate evaluation | Holdout from 2024-08-12: return 1.46%, Sharpe 0.77, drawdown -0.82%, 13 trades | Research only | Preliminary support, but insufficient trade count (<30). Extend history/universe or wait for additional observations before any paper-trading decision. |
| ATR breakout v1 QQQ rolling validation | Same fixed rules across four consecutive unseen windows | Average Sharpe 1.38, worst drawdown -0.82%, 26 trades | Research only | Strong preliminary robustness, but remains below the 30-trade minimum. Do not lower the threshold; gather additional evidence. |

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
