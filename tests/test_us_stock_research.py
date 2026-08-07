from quant_ai_trader.workflows.stocks.universe import US_STOCK_UNIVERSE


def test_stock_universe_is_frozen_unique_and_has_thirty_names():
    assert len(US_STOCK_UNIVERSE) == 30
    assert len(set(US_STOCK_UNIVERSE)) == 30
    assert "SPY" not in US_STOCK_UNIVERSE
