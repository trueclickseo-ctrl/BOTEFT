# Quant AI Trader

Research-first Python framework for ETF and large-cap quantitative trading. It uses Saxo OpenAPI market data, validates models against time-aware research gates, compares strategies honestly, and keeps execution disabled until explicit safety controls are satisfied.

> This software is for research and paper-trading workflows. It is not investment advice and does not auto-authorize live trading.

## Current status

| Area | Status |
|---|---|
| Saxo daily data, UIC lookup, SQLite storage | Implemented |
| Technical and market-context features | Implemented |
| LightGBM target-before-stop research | Implemented; current QQQ and pooled v1 results rejected |
| Single-ETF and cross-sectional backtests | Implemented |
| Risk limits, logging, readiness, drift and reconciliation | Implemented |
| Dashboard, FastAPI, Docker, CI | Implemented |
| Live order routing | Intentionally disabled by default |

See [STRATEGY_RESEARCH.md](STRATEGY_RESEARCH.md) for the permanent experiment register, including failed variants that must not be rerun unchanged.

## Setup

Python 3.12+ is required.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## Saxo simulation setup

Never put credentials in Git or chat. In the same PowerShell session used to run commands:

```powershell
$env:SAXO_ENVIRONMENT = "sim"
$env:SAXO_ACCESS_TOKEN = "your-token"
```

For a 24-hour simulation token, create a local `.env` file from the template. It is ignored by Git and loaded automatically by every Saxo command:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `SAXO_ACCESS_TOKEN`, `SAXO_ENVIRONMENT=sim`, and your verified `SAXO_INSTRUMENTS_JSON` in `.env`. Replace the token when Saxo expires it; never commit or share `.env`.

Resolve verified UICs first:

```powershell
.\.venv\Scripts\python.exe -m quant_ai_trader.data.instrument_lookup SPY QQQ IWM XLK XLF
```

Then set the mapping using only real numeric UICs:

```powershell
$env:SAXO_INSTRUMENTS_JSON = '{"SPY":{"uic":36590,"asset_type":"Etf"},"QQQ":{"uic":4328771,"asset_type":"Etf"}}'
```

## Daily data and research workflow

```powershell
# Sync data. End date is exclusive.
.\.venv\Scripts\python.exe -m quant_ai_trader.main --start 2021-08-01 --end 2026-08-08 --symbols SPY QQQ IWM XLK XLF

# Daily incremental refresh after the initial history load.
.\.venv\Scripts\python.exe -m quant_ai_trader.main --incremental --start 2021-08-01 --end 2026-08-08 --symbols SPY QQQ IWM XLK XLF

# Train/evaluate a single ETF model.
.\.venv\Scripts\python.exe -m quant_ai_trader.workflows.research --symbol QQQ

# Pooled, date-safe multi-ETF research.
.\.venv\Scripts\python.exe -m quant_ai_trader.workflows.research --symbol QQQ IWM XLK XLF

# Cross-sectional portfolio strategy evaluation.
.\.venv\Scripts\python.exe -m quant_ai_trader.workflows.cross_sectional --symbols QQQ IWM XLK XLF
```

The research-only daily monitor refreshes mapped Saxo symbols and reruns fixed QQQ breakout validation. It never submits orders:

```powershell
.\.venv\Scripts\python.exe -c "from quant_ai_trader.workflows.daily_monitor import run; print(run(['SPY','QQQ','IWM','XLK','XLF']))"
```

The ML label asks whether a +6% target is reached before a -3% stop within 30 sessions. Model promotion requires at least 100 OOS observations, ROC-AUC >= 0.52, and average precision >= 0.05. Rejected models are logged and backtested but never saved as signal models.

## Strategies and results

| Strategy | Current result | Decision |
|---|---|---|
| AI target-before-stop, pooled v1 | ROC-AUC 0.5062; 4,053 OOS observations | Rejected |
| Momentum baseline | QQQ return 5.24%, Sharpe 0.83 | Research benchmark |
| Cross-sectional ranking v1 | Sharpe 0.12; drawdown -36.97% | Rejected |
| Cross-sectional ranking v2 defensive | Return 21.66%, Sharpe 0.43; drawdown -31.79% | Research only; not approved |
| ATR breakout v1 | QQQ rolling validation: Sharpe 1.38, drawdown -0.82%, 26 trades; weak/negative on IWM | QQQ research candidate only; below 30-trade gate |

The full rationale and experiment template are maintained in `STRATEGY_RESEARCH.md`.

### Full-universe passive benchmark

These runs use the same historical sample, 10% allocation, and cost model as the active-strategy research. `number_of_trades = 0` is expected: this is a passive benchmark rather than an order-by-order strategy.

| ETF | Total return | Annual return | Sharpe | Maximum drawdown |
|---|---:|---:|---:|---:|
| SPY | 13.87% | 2.00% | 0.80 | -3.58% |
| QQQ | 23.06% | 3.21% | 0.83 | -6.09% |
| IWM | 3.49% | 0.69% | 0.34 | -3.58% |
| DIA | 4.16% | 0.86% | 0.56 | -2.24% |
| XLK | 14.14% | 2.68% | 0.80 | -3.85% |
| XLF | 5.75% | 1.13% | 0.56 | -2.99% |
| XLE | 13.55% | 2.71% | 0.68 | -4.66% |
| XLV | 1.01% | 0.21% | 0.15 | -2.10% |
| XLI | 6.93% | 1.42% | 0.72 | -2.57% |
| XLY | 3.02% | 0.63% | 0.28 | -4.61% |
| XLP | 1.85% | 0.39% | 0.28 | -1.98% |
| TLT | -4.34% | -0.93% | -0.80 | -4.71% |
| GLD | 15.55% | 3.08% | 0.99 | -4.72% |
| SLV | 23.16% | 4.48% | 0.63 | -14.06% |

This is the hurdle for future active strategies; a positive result alone is insufficient if passive exposure produced a better risk-adjusted return with lower complexity.

Run the fixed ATR-breakout versus its passive benchmark across all stored ETFs with one command:

```powershell
.\.venv\Scripts\python.exe -m quant_ai_trader.workflows.breakout_universe
```

The result includes per-ETF return, Sharpe, drawdown, trade count, evidence status, and a conservative verdict. It records research runs only and always returns `paper_trading_approved: False`.

The first full-universe run found no approval candidate. QQQ and SLV each met the standalone 30-trade/Sharpe/drawdown gate, but their passive benchmarks delivered materially higher total returns. The breakout system is therefore retained only as a lower-drawdown research reference, not an execution strategy.

### Next distinct strategy: dual momentum rotation

`dual_momentum_rotation_v1` rebalances monthly into the single ETF with the strongest positive trailing 252-session momentum. When every ETF has non-positive momentum, it moves fully to cash. The selection uses the prior close, charges costs on every holding change, and compares its result with a fully invested equal-weight benchmark on the same common sample. It is research-only.

```powershell
.\.venv\Scripts\python.exe -m quant_ai_trader.workflows.dual_momentum
```

The initial full-universe run returned 189.21% with a 0.87 Sharpe, ahead of equal weight's 68.69% and 0.85 Sharpe. However, its -42.45% drawdown exceeds the strict -20% portfolio limit, so it is rejected for paper trading and must not be retried unchanged.

### Risk-targeted dual momentum

`risk_targeted_dual_momentum_v1` is a separate, unlevered variant with a fixed 10% annual volatility budget, assessed at each monthly rebalance using only prior returns.

```powershell
.\.venv\Scripts\python.exe -m quant_ai_trader.workflows.risk_targeted_dual_momentum
```

Its first full-universe run achieved 60.85% total return, 0.98 Sharpe, and -14.39% drawdown. It passes the risk limit and improves risk-adjusted return versus equal weight, but trails equal weight's 68.69% total return; it remains research-only.

## Safety controls

- No look-ahead fills; signal entries execute next open in the daily backtester.
- Data checks reject invalid OHLCV, duplicate timestamps, and invalid price ranges; outlier filtering uses rolling past-only statistics.
- Portfolio limits: 1% risk/trade, 10 positions, 10% per ETF, 30% per sector.
- `runtime/KILL_SWITCH` blocks all broker submissions immediately.
- Live submission requires code-level enablement plus `SAXO_ALLOW_LIVE_TRADING=true`.
- Saxo net positions must reconcile with local positions before further orders.
- Feature drift is flagged at a three-standard-deviation mean shift.

## Dashboard and API

```powershell
.\.venv\Scripts\streamlit.exe run quant_ai_trader/dashboard/app.py
.\.venv\Scripts\uvicorn.exe quant_ai_trader.api.app:app --reload
```

Dashboard: `http://localhost:8501`  
API: `http://localhost:8000`

API endpoints: `/health`, `/readiness`, `/rankings`, `/backtests/{symbol}`, `/leaderboard`, `/strategy-history`, `/portfolio`.

`/strategy-history` returns individual recorded runs with their metrics, while `/leaderboard` aggregates strategy averages. Inspect both before judging a strategy: an aggregate can hide weak symbols or sparse trade samples.

## Daily research monitor

The monitor incrementally synchronizes completed Saxo daily bars, reruns fixed QQQ breakout rolling validation, and logs the result. It treats weekends, holidays, and incomplete daily bars as normal zero-update sessions.

```powershell
.\.venv\Scripts\python.exe -c "from quant_ai_trader.workflows.daily_monitor import run; print(run(['SPY','QQQ','IWM','XLK','XLF']))"
```

The monitor is research-only and contains no order-submission path. The QQQ ATR breakout remains below its 30-trade minimum; its rules must remain fixed while evidence accumulates.

## Containers and CI

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Data, artifacts, and logs are mounted locally, not included in images. GitHub Actions runs tests on Python 3.12.

## Project layout

```
quant_ai_trader/
  data/           Saxo provider, SQLite, data quality, UIC lookup
  features/       technical features, labels, dataset pipeline
  models/         LightGBM training, prediction, gates, drift checks
  strategies/     AI rules, baselines, cross-sectional rankings
  backtesting/    single-ETF and portfolio backtests
  risk/           sizing, exposure controls, portfolio state
  execution/      paper/Saxo interfaces, safety, reconciliation
  dashboard/      Streamlit interface and research services
  api/            FastAPI service
  workflows/      repeatable research commands
```
