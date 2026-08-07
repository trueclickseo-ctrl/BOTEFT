"""Streamlit research dashboard. Run with: streamlit run quant_ai_trader/dashboard/app.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit executes a script with its directory first on sys.path. Add the
# repository root when launched as ``streamlit run quant_ai_trader/dashboard/app.py``.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from quant_ai_trader.config.settings import Settings
from quant_ai_trader.dashboard.data_service import build_rankings, run_model_backtest
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.models.model_manager import ModelManager
from quant_ai_trader.risk.portfolio_manager import PortfolioManager
from quant_ai_trader.operations.readiness import assess_readiness
from quant_ai_trader.workflows.paper_readiness import run as paper_readiness
from quant_ai_trader.workflows.stocks.decision import run as stock_decision


def main() -> None:
    st.set_page_config(page_title="Quant AI Trader", page_icon="📈", layout="wide")
    st.title("Quant AI Trader")
    st.caption("Research dashboard — signals are not broker orders.")
    settings = Settings()
    repository = MarketDataRepository(settings.database_path)
    repository.initialize()
    manager = ModelManager(settings.model_directory)
    readiness = assess_readiness(repository, manager)
    st.sidebar.success("Paper ready" if readiness.ready_for_paper else "Paper trading not ready")
    st.sidebar.json(readiness.checks)
    st.sidebar.header("Research data")
    st.sidebar.write(f"Database: `{settings.database_path}`")
    st.sidebar.write(f"Model directory: `{settings.model_directory}`")
    _render_stock_decision()
    try:
        artifact = manager.load()
    except FileNotFoundError:
        st.info("No trained model artifact found. Complete the model-training workflow before rankings and backtests are available.")
        _render_portfolio()
        _render_governance()
        _render_leaderboard(repository)
        return

    rankings = build_rankings(repository, artifact)
    st.header("ETF rankings")
    if rankings.empty:
        st.warning("No rankable instruments. Sync data for SPY and at least one ETF with sufficient history.")
    else:
        st.dataframe(rankings, use_container_width=True, hide_index=True)
        selected = st.selectbox("Backtest ETF", rankings["symbol"].tolist())
        if st.button("Run model backtest", type="primary"):
            result = run_model_backtest(repository, artifact, selected)
            metrics = result.metrics
            columns = st.columns(4)
            columns[0].metric("Total return", f"{metrics['total_return']:.2%}")
            columns[1].metric("Sharpe", f"{metrics['sharpe_ratio']:.2f}")
            columns[2].metric("Maximum drawdown", f"{metrics['maximum_drawdown']:.2%}")
            columns[3].metric("Trades", int(metrics["number_of_trades"]))
            st.line_chart(result.equity_curve)
            st.dataframe(result.trades, use_container_width=True, hide_index=True)
    _render_portfolio()
    _render_governance()
    _render_leaderboard(repository)


def _render_leaderboard(repository: MarketDataRepository) -> None:
    st.header("Strategy leaderboard")
    leaderboard = repository.strategy_leaderboard()
    if leaderboard.empty: st.caption("Run a research cycle to populate comparable strategy results.")
    else: st.dataframe(leaderboard, use_container_width=True, hide_index=True)
    with st.expander("Strategy run history"):
        history = repository.strategy_history()
        if history.empty: st.caption("No recorded research runs.")
        else: st.dataframe(history, use_container_width=True, hide_index=True)


def _render_portfolio() -> None:
    st.header("Portfolio allocation")
    portfolio = st.session_state.setdefault("portfolio", PortfolioManager())
    if not portfolio.positions:
        st.caption("No paper or live positions are attached to this dashboard session yet.")
        return
    rows = [{"symbol": p.symbol, "sector": p.sector, "shares": p.shares, "market_value": p.market_value} for p in portfolio.positions.values()]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_stock_decision() -> None:
    st.header("Stock decision engine")
    try:
        decision = stock_decision()
    except (FileNotFoundError, ValueError) as error:
        st.warning(f"Stock decision unavailable: {error}")
        return
    action = decision["action"]
    symbol = decision["symbol"] or "CASH"
    if action in {"BUY", "ROTATE"} and decision["submission_authorized"]:
        st.success(f"{action} {symbol}")
    elif action == "HOLD":
        st.info(f"HOLD {symbol}")
    elif action == "CANDIDATE":
        st.warning(f"CANDIDATE {symbol} — NOT ACTIONABLE (raw signal: {decision['raw_signal_action']})")
    else:
        st.warning(action)
    columns = st.columns(4)
    columns[0].metric("Target weight", f"{decision['target_weight']:.2%}")
    columns[1].metric("Momentum", f"{decision['trailing_momentum']:.2%}" if decision["trailing_momentum"] is not None else "n/a")
    columns[2].metric("Last rebalance", decision["last_rebalance_date"])
    columns[3].metric("Next review", decision["next_review_date"])
    st.caption(decision["reason"])
    if decision["submission_authorized"]:
        st.success("SIM submission gates are satisfied. This dashboard still does not submit orders.")
    else:
        st.warning("Signal active; order submission blocked.")
        with st.expander("Execution blockers"):
            st.json(decision["blockers"])


def _render_governance() -> None:
    """Expose fail-closed order blockers beside research results."""
    st.header("Paper-trading governance")
    report = paper_readiness()
    if report["ready"]:
        st.success("Paper-trading preflight passed. No order is submitted from this dashboard.")
    else:
        st.warning("Paper trading is blocked. Research signals are not orders.")
        st.dataframe([{"blocker": blocker} for blocker in report["blockers"]], use_container_width=True, hide_index=True)
    with st.expander("Preflight checks"):
        st.json(report["checks"])


if __name__ == "__main__":
    main()
