from quant_ai_trader.workflows.stocks.saxo_reconciliation import compare_snapshots


def test_empty_broker_account_safely_establishes_implicit_flat_state():
    result = compare_snapshots({}, None)
    assert result["matched"]
    assert result["local_state"] == "implicit_flat_verified"


def test_missing_local_ledger_cannot_hide_managed_broker_position():
    result = compare_snapshots({"CAT": 2, "SPY": 4}, None)
    assert not result["matched"]
    assert result["ignored_external_positions"] == ["SPY"]
    assert "CAT" in result["differences"][0]


def test_loaded_ledger_must_match_managed_positions_exactly():
    assert compare_snapshots({"CAT": 2}, {"CAT": 2})["matched"]
    assert not compare_snapshots({"CAT": 2}, {"CAT": 1})["matched"]


def test_preexisting_managed_symbols_can_be_scoped_as_external_baseline():
    result = compare_snapshots({"UNH": 1, "V": 1}, {}, {"UNH": 1, "V": 1})
    assert result["matched"]
    changed = compare_snapshots({"UNH": 2, "V": 1}, {}, {"UNH": 1, "V": 1})
    assert not changed["matched"]
