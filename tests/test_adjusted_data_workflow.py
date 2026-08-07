from quant_ai_trader.workflows.us_v2_adjusted_data import EXPANDED_UNIVERSE


def test_adjusted_expanded_universe_is_frozen_at_twenty_symbols():
    assert len(EXPANDED_UNIVERSE) == 20
    assert "IEF" in EXPANDED_UNIVERSE
    assert len(set(EXPANDED_UNIVERSE)) == 20
