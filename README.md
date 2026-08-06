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

The ML label asks whether a +6% target is reached before a -3% stop within 30 sessions. Model promotion requires at least 100 OOS observations, ROC-AUC >= 0.52, and average precision >= 0.05. Rejected models are logged and backtested but never saved as signal models.

## Strategies and results

| Strategy | Current result | Decision |
|---|---|---|
| AI target-before-stop, pooled v1 | ROC-AUC 0.5062; 4,053 OOS observations | Rejected |
| Momentum baseline | QQQ return 5.24%, Sharpe 0.83 | Research benchmark |
| Cross-sectional ranking v1 | Sharpe 0.12; drawdown -36.97% | Rejected |
| Cross-sectional ranking v2 defensive | Return 21.66%, Sharpe 0.43; drawdown -31.79% | Research only; not approved |

The full rationale and experiment template are maintained in `STRATEGY_RESEARCH.md`.

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

API endpoints: `/health`, `/readiness`, `/rankings`, `/backtests/{symbol}`, `/leaderboard`, `/portfolio`.

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
