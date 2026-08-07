from quant_ai_trader.execution.allocation import validate_target_weights


def test_allocation_validation_blocks_etf_and_sector_limit_breaches():
    result = validate_target_weights({"QQQ": .15, "XLK": .2, "CASH": .65}, {"QQQ": "Broad", "XLK": "Technology"})
    assert not result.approved and "QQQ: maximum ETF allocation exceeded" in result.blockers
