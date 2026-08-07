from quant_ai_trader.workflows.stocks.large_universes import NASDAQ_100,SP_500_TOP_50

def test_large_stock_universes_are_separate_and_frozen():
    assert len(NASDAQ_100)==101
    assert len(set(NASDAQ_100))==101
    assert len(SP_500_TOP_50)==50
    assert len(set(SP_500_TOP_50))==50
