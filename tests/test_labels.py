import pandas as pd

from quant_ai_trader.features.labels import create_target_stop_labels


def test_labels_target_before_stop_and_conservative_ambiguous_bar():
    index = pd.bdate_range("2024-01-01", periods=5)
    bars = pd.DataFrame({
        "adjusted_close": [100, 100, 100, 100, 100],
        "high": [101, 106, 106, 106, 106],
        "low": [99, 99, 94, 94, 94],
    }, index=index)
    result = create_target_stop_labels(bars, target_return=.05, stop_loss=.03, holding_period_days=2)
    assert result.iloc[0]["target_hit_before_stop"] == 1
    # The second signal sees a bar crossing both target and stop; stop wins conservatively.
    assert result.iloc[1]["target_hit_before_stop"] == 0
    assert pd.isna(result.iloc[-1]["target_hit_before_stop"])
