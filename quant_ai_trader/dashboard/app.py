"""Streamlit research dashboard. Run with: streamlit run quant_ai_trader/dashboard/app.py."""

from __future__ import annotations

import streamlit as st

from quant_ai_trader.config.settings import Settings
from quant_ai_trader.dashboard.data_service import build_rankings, run_model_backtest
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.models.model_manager import ModelManager
from quant_ai_trader.risk.portfolio_manager import PortfolioManager


def main() -> None:
    st.set_page_config(page_title="Quant AI Trader", page_icon="📈", layout="wide")
    st.title("Quant AI Trader")
    st.caption("Research dashboard — signals are not broker orders.")
    settings = Settings()
    repository = MarketDataRepository(settings.database_path)
    repository.initialize()
    manager = ModelManager(settings.model_directory)
    st.sidebar.header("Research data")
    st.sidebar.write(f"Database: `{settings.database_path}`")
    st.sidebar.write(f"Model directory: `{settings.model_directory}`")
    try:
        artifact = manager.load()
    except FileNotFoundError:
        st.info("No trained model artifact found. Complete the model-training workflow before rankings and backtests are available.")
        _render_portfolio()
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


def _render_portfolio() -> None:
    st.header("Portfolio allocation")
    portfolio = st.session_state.setdefault("portfolio", PortfolioManager())
    if not portfolio.positions:
        st.caption("No paper or live positions are attached to this dashboard session yet.")
        return
    rows = [{"symbol": p.symbol, "sector": p.sector, "shares": p.shares, "market_value": p.market_value} for p in portfolio.positions.values()]
    st.dataframe(rows, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
