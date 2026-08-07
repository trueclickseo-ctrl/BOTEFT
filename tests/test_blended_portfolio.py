import pandas as pd
import pytest
from quant_ai_trader.backtesting.blended_portfolio import blend_equity_curves


def test_static_blend_sits_between_component_end_values():
    index = pd.bdate_range("2024-01-01", periods=3)
    curve, metrics = blend_equity_curves(pd.Series([100, 110, 120], index=index), pd.Series([100, 105, 110], index=index))
    assert curve.iloc[-1] == pytest.approx(115_000) and metrics["total_return"] == pytest.approx(.15)
