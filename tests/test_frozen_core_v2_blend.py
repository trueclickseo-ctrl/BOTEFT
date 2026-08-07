import numpy as np
import pandas as pd

from quant_ai_trader.strategies.frozen_core_v2_blend import (
    FrozenCoreV2BlendConfig,
    build_frozen_core_v2_weights,
)


def _prices(periods=320):
    dates = pd.bdate_range("2020-01-01", periods=periods)
    x = np.arange(periods)
    return pd.DataFrame({
        "SPY": 100 * np.exp(.0005 * x + .01 * np.sin(x / 8)),
        "QQQ": 100 * np.exp(.0008 * x + .015 * np.sin(x / 7)),
        "TLT": 100 * np.exp(.0002 * x + .008 * np.sin(x / 11)),
        "GLD": 100 * np.exp(.0003 * x + .006 * np.sin(x / 13)),
    }, index=dates)


def test_frozen_blend_is_capped_unlevered_and_keeps_cash():
    config = FrozenCoreV2BlendConfig(defensive_holdings=3)
    weights, components = build_frozen_core_v2_weights(_prices(), config)
    assert weights.max().max() <= config.maximum_etf_weight + 1e-12
    assert weights.min().min() >= 0
    assert weights.sum(axis=1).max() <= 1 + 1e-12
    assert (components["unconstrained"] >= weights - 1e-12).all().all()


def test_frozen_blend_uses_next_session_weights():
    prices = _prices()
    config = FrozenCoreV2BlendConfig(defensive_holdings=3)
    weights, _ = build_frozen_core_v2_weights(prices, config)
    first_active = weights.sum(axis=1).ne(0).idxmax()
    # Core's first signal is formed after 21 completed observations and may
    # only become active on the following row.
    assert prices.index.get_loc(first_active) >= config.sleeve_volatility_lookback_days + 2


def test_consolidation_never_increases_target_turnover():
    weights, components = build_frozen_core_v2_weights(
        _prices(), FrozenCoreV2BlendConfig(defensive_holdings=3)
    )
    independent = sum(
        float(frame.diff().abs().sum(axis=1).sum())
        for name, frame in components.items() if name != "unconstrained"
    )
    consolidated = float(weights.diff().abs().sum(axis=1).sum())
    assert consolidated <= independent + 1e-12


def test_frozen_allocations_cannot_be_changed_silently():
    try:
        FrozenCoreV2BlendConfig(defensive_v2_allocation=.40)
    except ValueError as error:
        assert "sum to one" in str(error)
    else:
        raise AssertionError("Invalid frozen allocations were accepted")


def test_core_only_builder_does_not_require_spy():
    prices = _prices().drop(columns="SPY")
    config = FrozenCoreV2BlendConfig(
        core_equal_weight_allocation=.5,
        dual_momentum_allocation=.5,
        defensive_v2_allocation=0,
    )
    weights, _ = build_frozen_core_v2_weights(prices, config)
    assert list(weights.columns) == list(prices.columns)
    assert weights.max().max() <= .10 + 1e-12
