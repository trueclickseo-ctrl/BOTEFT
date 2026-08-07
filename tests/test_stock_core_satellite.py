import numpy as np
import pandas as pd

from quant_ai_trader.strategies.stocks.core_satellite import (
    StockCoreSatelliteConfig, build_stock_core_satellite_weights,
)


def _prices(periods=320):
    dates = pd.bdate_range("2020-01-01", periods=periods)
    x = np.arange(periods)
    return pd.DataFrame({
        "A": 100 * np.exp(.0008 * x + .01 * np.sin(x / 8)),
        "B": 100 * np.exp(.0004 * x + .012 * np.sin(x / 11)),
        "C": 100 * np.exp(.0002 * x + .009 * np.sin(x / 13)),
    }, index=dates)


def test_stock_weights_are_capped_and_next_session_only():
    prices = _prices()
    weights, unconstrained = build_stock_core_satellite_weights(prices)
    assert weights.max().max() <= .10 + 1e-12
    assert weights.sum(axis=1).max() <= 1 + 1e-12
    assert (unconstrained >= weights - 1e-12).all().all()
    first_active = weights.sum(axis=1).ne(0).idxmax()
    assert prices.index.get_loc(first_active) >= 22


def test_stock_sleeve_allocations_are_frozen():
    try:
        StockCoreSatelliteConfig(core_allocation=.60)
    except ValueError as error:
        assert "sum to one" in str(error)
    else:
        raise AssertionError("Invalid stock allocations were accepted")
