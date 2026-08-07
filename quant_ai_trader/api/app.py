"""Read-only HTTP API for dashboard and future client integrations."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

from quant_ai_trader.config.settings import Settings
from quant_ai_trader.dashboard.data_service import build_rankings, run_model_backtest
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.models.model_manager import ModelManager
from quant_ai_trader.risk.portfolio_manager import PortfolioManager
from quant_ai_trader.operations.readiness import assess_readiness
from quant_ai_trader.workflows.paper_readiness import run as paper_readiness
from quant_ai_trader.execution.saxo_oauth import SaxoOAuthClient, SaxoOAuthSettings


def create_app() -> FastAPI:
    load_dotenv()
    settings = Settings()
    repository, manager = MarketDataRepository(settings.database_path), ModelManager(settings.model_directory)
    repository.initialize()
    app = FastAPI(title="Quant AI Trader API", version="0.1.0")
    app.state.portfolio = PortfolioManager()
    try:
        app.state.saxo_oauth = SaxoOAuthClient(SaxoOAuthSettings.from_environment())
    except (RuntimeError, ValueError, PermissionError):
        app.state.saxo_oauth = None

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "symbols": repository.list_symbols(), "model_available": (manager.directory / "target_stop_lgbm.joblib").exists()}

    @app.get("/rankings")
    def rankings() -> list[dict[str, object]]:
        try:
            return json.loads(build_rankings(repository, manager.load()).to_json(orient="records", date_format="iso"))
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.get("/backtests/{symbol}")
    def backtest(symbol: str) -> dict[str, object]:
        try:
            result = run_model_backtest(repository, manager.load(), symbol.upper())
            return {
                "symbol": symbol.upper(), "metrics": result.metrics,
                "equity_curve": json.loads(result.equity_curve.to_json(date_format="iso")),
                "trades": json.loads(result.trades.to_json(orient="records", date_format="iso")),
            }
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.get("/portfolio")
    def portfolio() -> dict[str, object]:
        state = app.state.portfolio
        return {"cash": state.cash, "equity": state.equity, "positions": [vars(p) | {"market_value": p.market_value} for p in state.positions.values()]}

    @app.get("/leaderboard")
    def leaderboard() -> list[dict[str, object]]:
        return json.loads(repository.strategy_leaderboard().to_json(orient="records"))

    @app.get("/strategy-history")
    def strategy_history() -> list[dict[str, object]]:
        return json.loads(repository.strategy_history().to_json(orient="records", date_format="iso"))

    @app.get("/readiness")
    def readiness() -> dict[str, object]:
        return vars(assess_readiness(repository, manager))

    @app.get("/paper-readiness")
    def paper_readiness_status() -> dict[str, object]:
        return paper_readiness()

    @app.get("/auth/saxo/login")
    def saxo_login() -> RedirectResponse:
        if app.state.saxo_oauth is None:
            raise HTTPException(status_code=503, detail="SAXO_APP_KEY is not configured")
        return RedirectResponse(app.state.saxo_oauth.authorization_url(), status_code=302)

    @app.get("/auth/saxo/callback")
    def saxo_callback(code: str, state: str) -> dict[str, object]:
        if app.state.saxo_oauth is None:
            raise HTTPException(status_code=503, detail="SAXO_APP_KEY is not configured")
        try:
            token = app.state.saxo_oauth.exchange(code, state)
        except (PermissionError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"authenticated": True, "expires_in": token.get("expires_in")}

    @app.get("/auth/saxo/status")
    def saxo_status() -> dict[str, object]:
        if app.state.saxo_oauth is None:
            return {"configured": False, "authenticated": False, "environment": "sim"}
        return app.state.saxo_oauth.status()

    return app


app = create_app()
