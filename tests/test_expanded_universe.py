from quant_ai_trader.workflows.us_v2_expanded_universe import ADDITIONS, EXPANDED_UNIVERSE


def test_expanded_universe_is_predeclared_and_unique():
    assert ADDITIONS == ("TIP", "PDBC", "EFA", "EEM", "VNQ")
    assert len(EXPANDED_UNIVERSE) == 19
    assert len(set(EXPANDED_UNIVERSE)) == len(EXPANDED_UNIVERSE)
