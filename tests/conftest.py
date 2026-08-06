import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_bars() -> pd.DataFrame:
    index = pd.bdate_range("2023-01-02", periods=260)
    close = pd.Series(np.linspace(100, 140, len(index)) + np.sin(np.arange(len(index))), index=index)
    return pd.DataFrame({
        "open": close - 0.5,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": np.linspace(1_000_000, 2_000_000, len(index)),
        "adjusted_close": close,
    }, index=index)

