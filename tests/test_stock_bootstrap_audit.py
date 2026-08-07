import numpy as np
import pandas as pd

from quant_ai_trader.workflows.stocks.bootstrap_audit import (
    BootstrapConfig, bootstrap_daily_returns, stationary_bootstrap_indices,
)


def test_stationary_bootstrap_is_reproducible_and_bounded():
    first = stationary_bootstrap_indices(100, 20, np.random.default_rng(7))
    second = stationary_bootstrap_indices(100, 20, np.random.default_rng(7))
    assert np.array_equal(first, second)
    assert first.min() >= 0 and first.max() < 100


def test_bootstrap_audit_is_fail_closed_and_rejection_only():
    rng = np.random.default_rng(11)
    returns = pd.Series(rng.normal(-.0002, .02, 756))
    result = bootstrap_daily_returns(returns, BootstrapConfig(samples=100, seed=9))
    assert result["paper_approved"] is False
    assert result["robustness_gate_pass"] is False
    assert 0 <= result["joint_gate_pass_probability"] <= 1


def test_bootstrap_requires_one_year_of_returns():
    try:
        bootstrap_daily_returns(pd.Series([.01] * 20), BootstrapConfig(samples=10))
    except ValueError as error:
        assert "252" in str(error)
    else:
        raise AssertionError("Short return history must be rejected")
