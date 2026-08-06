# Quant AI Trader — Phase 1

Production-oriented foundation for an AI ETF quantitative research and trading platform. Phase 1 delivers reliable daily market-data ingestion, SQLite storage, technical indicators, market-context features, data-quality controls, and tests. Sprint 2 adds leakage-aware ML labelling and LightGBM walk-forward research.

## Design choices

- **Production data source:** `SaxoBankProvider` uses Saxo OpenAPI chart data. The provider is isolated behind a small interface, retaining Yahoo Finance only as an explicit local-development fallback.
- **Canonical data store:** daily OHLCV data is normalized into SQLite with idempotent symbol/date upserts. PostgreSQL can be introduced via a repository implementation without changing feature code.
- **No look-ahead filling:** cleaning only forward-fills; it never back-fills future observations into historical rows. Indicators only use current and past bars.
- **Robust outlier handling:** extreme numeric values are masked by median absolute deviation before historical forward fill. Raw bars remain retained in the database.
- **Point-in-time fundamentals:** the placeholder explicitly reserves this for release-timestamped data, preventing accidental fundamental-data leakage.

## Project layout

```
quant_ai_trader/
  config/settings.py                 Runtime configuration and ETF universe
  data/market_data.py                Provider interface + Yahoo Finance adapter
  data/database.py                   SQLite daily-bar repository
  features/technical_features.py     SMA, EMA, RSI, MACD, ATR, bands, momentum, volatility
  features/feature_pipeline.py       Market context and data-quality pipeline
  features/labels.py                 Target-before-stop labels from future OHLC bars
  models/train_model.py              Purged walk-forward LightGBM training
  models/predict.py                  Latest-row research prediction
  models/model_manager.py            Versioned joblib model artifacts
  strategies/etf_strategy.py         Probability, risk/reward, and market-regime rules
  backtesting/backtester.py          Next-open fills, costs, target/stop exits, trade ledger
  backtesting/performance.py         Return, Sharpe, drawdown, win-rate, profit-factor metrics
  risk/position_sizing.py            Whole-share risk and allocation constrained sizing
  risk/portfolio_manager.py          Cash, positions, market marks, and sector exposure state
  risk/risk_manager.py               Pre-trade limits and explicit order approval decisions
  api/app.py                          Read-only FastAPI rankings, backtest, and portfolio endpoints
  dashboard/app.py                    Streamlit research dashboard
  execution/broker_interface.py       Saxo v2 pre-check/order adapter (submission disabled by default)
  execution/paper_trading.py          Deterministic paper-order lifecycle
  observability/logging.py             Rotating structured JSON audit logs
  main.py                            Collection/feature-generation CLI
tests/                               Unit tests
```

## Setup

Python 3.12+ is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Collect daily data through Saxo OpenAPI

The end date is exclusive, matching the provider convention.

Configure the token and the **verified** UIC/asset-type mapping obtained from Saxo's instrument reference data. Never commit tokens or account identifiers.

```powershell
$env:SAXO_ENVIRONMENT = "sim" # use "live" only after production controls are approved
$env:SAXO_ACCESS_TOKEN = "your-short-lived-openapi-token"
$env:SAXO_INSTRUMENTS_JSON = '{"SPY":{"uic":123456,"asset_type":"Etf"},"QQQ":{"uic":234567,"asset_type":"Etf"}}'
python -m quant_ai_trader.main --start 2020-01-01 --end 2026-01-01 --symbols SPY QQQ
```

The UIC values above are illustrative—do not use them in production. Saxo identifies instruments by both UIC and asset type, and the correct ETF listing depends on the permitted trading venue and account setup. The default is Saxo simulation; the code fails closed when a token or mapping is absent.

For local, non-production development only:

```powershell
python -m quant_ai_trader.main --provider yahoo --start 2020-01-01 --end 2026-01-01 --symbols SPY QQQ
```

This creates `data/quant_ai_trader.sqlite3` locally, which is ignored by Git. `SPY` is automatically used as market context if included in the stored data. VIX support is ready via `build_feature_dataset(..., vix_bars=...)` using a mapped volatility instrument.

Saxo chart samples provide OHLCV but not a separate adjusted-close field. Phase 1 records the raw close in `adjusted_close` with that limitation documented; before training, Phase 2 will add a versioned corporate-actions adjustment pipeline. Saxo documents that chart history can be corrected, so a future synchronizer will track chart `DataVersion` and re-fetch corrected series.

## Run tests

```powershell
python -m pytest -q
```

## Phase 1 feature set

Technical features include SMA 20/50/200, EMA 20, RSI 14, MACD/signal/histogram, ATR 14, Bollinger bands, 20-day momentum, annualized 20-day volatility, and five-day volume change. Market-context features include SPY 50-day trend and 20-day return, plus optional VIX level.

Sector performance and breadth need a defined constituent/universe dataset and will be added alongside training-label design in Phase 2, where their point-in-time construction can be validated rigorously.

## Sprint 2: model research

`create_target_stop_labels` labels a signal date as positive only when its +6% target is reached before its -3% stop within 30 trading days. When a daily bar crosses both levels, the label is deliberately negative because daily data cannot establish intraday order. Incomplete future horizons remain unlabelled. The original +5% / -3% illustration has a 1.67 risk/reward ratio, so it cannot meet the required minimum ratio of 2.0; the default target is therefore +6%.

Training uses chronological `TimeSeriesSplit` folds with a 30-day purge gap so outcomes in the training fold do not overlap its validation period. It reports out-of-sample ROC-AUC, average precision, and Brier score, then persists the final model with its feature schema and target/stop metadata. Signals remain research-only until the backtesting and risk phases are complete.

## Sprint 3: strategy and backtesting

The ETF strategy enters only when buy probability is at least 75%, risk/reward is at least 2, and SPY's 50-day trend is positive. Signals are known at the close and fill at the next session's open. The backtester supports cash-based risk position sizing, 10% allocation caps, commission, slippage, stop/target exits, probability exits, maximum holding periods, an equity curve, and a closed-trade ledger. If target and stop occur on the same daily candle, the stop is assumed first.

## Sprint 4: portfolio risk controls

Every prospective order passes through `RiskManager` before it can be submitted. The default $100,000 account risks 1% per trade and rejects orders that exceed ten positions, 10% in an ETF, 30% in a sector, available cash, or the 2.0 risk/reward rule. Decisions include a machine-readable reason, enabling the future Saxo execution adapter to fail closed.

## Sprint 5: API and dashboard

Start the API and dashboard from the repository root:

```powershell
.\.venv\Scripts\uvicorn.exe quant_ai_trader.api.app:app --reload
.\.venv\Scripts\streamlit.exe run quant_ai_trader/dashboard/app.py
```

The API provides `GET /health`, `/rankings`, `/backtests/{symbol}`, and `/portfolio`. Both UI and API are read-only research surfaces: they require synced bars and a saved model artifact, and never submit Saxo orders.

## Sprint 6: execution, logs, and strategy leaderboard

Saxo orders use the v2 pre-check endpoint before the order endpoint. Live submission is disabled by default; use `PaperBroker` until reconciliation and account-specific safeguards are approved. `configure_logging()` writes rotating JSONL audit logs to `logs/` without secrets. Persist completed backtests with `MarketDataRepository.record_strategy_run(...)`; `strategy_leaderboard()` ranks strategies by average Sharpe, then average total return.

## Container deployment

Copy `.env.example` to `.env`, add only a simulation token and verified instrument mappings, then run:

```powershell
docker compose up --build
```

The API is available at `http://localhost:8000` and the dashboard at `http://localhost:8501`. Data, models, and logs are mounted to local directories and never baked into the image. GitHub Actions runs the complete test suite on Python 3.12 for every push and pull request.

## Repeatable research cycle

After syncing sufficient Saxo history for `SPY` and an ETF, run:

```powershell
.\.venv\Scripts\python.exe -m quant_ai_trader.workflows.research --symbol QQQ
```

This creates a labelled dataset, runs purged walk-forward training, saves the model artifact, backtests the strategy, writes an audit log, and records the result in the SQLite strategy leaderboard.
