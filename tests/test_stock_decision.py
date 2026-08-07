import pandas as pd

from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.stocks.decision import build_decision
from quant_ai_trader.workflows.stocks.universe import US_STOCK_UNIVERSE


def _database(tmp_path):
    path = tmp_path / "stocks.sqlite3"
    repository = MarketDataRepository(path); repository.initialize()
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    for number, symbol in enumerate(US_STOCK_UNIVERSE):
        growth = .0001 + number * .00002
        close = pd.Series([100 * (1 + growth) ** day for day in range(len(dates))], index=dates)
        bars = pd.DataFrame({"open": close, "high": close, "low": close, "close": close,
                             "adjusted_close": close, "volume": 1_000_000}, index=dates)
        repository.upsert_bars(symbol, bars)
    return path


def test_flat_account_gets_buy_decision_but_not_submission_authority(tmp_path):
    decision = build_decision(database_path=_database(tmp_path), current_quantities={})
    assert decision.action == "CANDIDATE"
    assert decision.raw_signal_action == "BUY"
    assert decision.symbol == US_STOCK_UNIVERSE[-1]
    assert decision.signal_is_active
    assert not decision.submission_authorized
    assert decision.strategy_status == "research_only"


def test_existing_candidate_gets_hold_and_whole_share_target(tmp_path):
    path = _database(tmp_path)
    first = build_decision(database_path=path)
    decision = build_decision(database_path=path, current_quantities={first.symbol: 2},
                              account_equity=10_000,
                              saxo_instruments={first.symbol: {"uic": 42, "asset_type": "Stock"}})
    assert decision.action == "CANDIDATE"
    assert decision.raw_signal_action == "HOLD"
    assert decision.current_quantity == 2
    assert decision.indicative_target_quantity >= 0
    assert decision.saxo_instrument["uic"] == 42


def test_explicit_tactical_holding_causes_rotation_not_core_holdings(tmp_path):
    path = _database(tmp_path)
    first = build_decision(database_path=path, current_quantities={US_STOCK_UNIVERSE[0]: 5})
    assert first.raw_signal_action == "BUY"
    rotated = build_decision(database_path=path, current_tactical_symbol=US_STOCK_UNIVERSE[0])
    assert rotated.action == "CANDIDATE"
    assert rotated.raw_signal_action == "ROTATE"
    assert US_STOCK_UNIVERSE[0] in rotated.reason
