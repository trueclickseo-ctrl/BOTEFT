from quant_ai_trader.config.universe import ETF_UNIVERSE, LARGE_CAP_UNIVERSE, sector_for

def test_universe_has_sector_metadata_for_etfs_and_large_caps():
    assert len(ETF_UNIVERSE) == 14
    assert len(LARGE_CAP_UNIVERSE) >= 5
    assert sector_for("qqq") == "Technology"
