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

## Strategy research

All strategy specifications, benchmark comparisons, test outcomes, rejected variants, and promotion decisions are maintained exclusively in [STRATEGY_RESEARCH.md](STRATEGY_RESEARCH.md). That document is the authoritative strategy decision log; this README describes how to install and operate the platform.

## Safety controls

- No look-ahead fills; signal entries execute next open in the daily backtester.
- Data checks reject invalid OHLCV, duplicate timestamps, and invalid price ranges; outlier filtering uses rolling past-only statistics.
- Portfolio limits: 1% risk/trade, 10 positions, 10% per ETF, 30% per sector.
- `runtime/KILL_SWITCH` blocks all broker submissions immediately.
- Live submission requires code-level enablement plus `SAXO_ALLOW_LIVE_TRADING=true`.
- Saxo net positions must reconcile with local positions before further orders.
- Feature drift is flagged at a three-standard-deviation mean shift.

Run the non-mutating paper-trading preflight before any future paper deployment:

```powershell
.\.venv\Scripts\python.exe -m quant_ai_trader.workflows.paper_readiness
```

The preflight is intentionally fail-closed. It reports the missing approval, reconciliation, account, or implementation requirement; it never submits an order.

The controlled SLV paper-pilot planner is also non-submitting; it returns `NO_TRADE` unless the fixed breakout condition is active:

```powershell
.\.venv\Scripts\python.exe -m quant_ai_trader.workflows.slv_paper_pilot
```

## Dashboard and API

```powershell
.\.venv\Scripts\streamlit.exe run quant_ai_trader/dashboard/app.py
.\.venv\Scripts\uvicorn.exe quant_ai_trader.api.app:app --reload
```

Dashboard: `http://localhost:8501`  
API: `http://localhost:8000`

API endpoints: `/health`, `/readiness`, `/paper-readiness`, `/rankings`, `/backtests/{symbol}`, `/leaderboard`, `/strategy-history`, `/portfolio`.

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
