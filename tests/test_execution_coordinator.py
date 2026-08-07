import pytest

from quant_ai_trader.execution.broker_interface import OrderRequest
from quant_ai_trader.execution.coordinator import ExecutionCoordinator
from quant_ai_trader.execution.idempotency import OrderIntentLedger
from quant_ai_trader.execution.reconciliation import ReconciliationResult


class Broker:
    def __init__(self, precheck=None):
        self.precheck_response = precheck or {"EstimatedTotalCost": 1000}
        self.placed = 0; self.cancelled = 0
    def precheck(self, order): return self.precheck_response
    def place(self, order): self.placed += 1; return {"OrderId": "123"}
    def cancel_order(self, account_key, order_id): self.cancelled += 1; return {"cancelled": True}


def order():
    return OrderRequest("SPY", 42, "Etf", "account", "Buy", 5, "approved", "botef-key")


def coordinator(tmp_path, broker=None):
    return ExecutionCoordinator(broker or Broker(), OrderIntentLedger(tmp_path / "ledger.json"), lambda strategy: None)


def test_submission_requires_reconciliation_and_operator_approval(tmp_path):
    service = coordinator(tmp_path)
    with pytest.raises(PermissionError, match="reconciled"):
        service.preview(order(), ReconciliationResult(False, ("mismatch",)))
    with pytest.raises(PermissionError, match="operator"):
        service.submit(order(), ReconciliationResult(True, ()), False)


def test_precheck_rejection_and_duplicate_submission_are_blocked(tmp_path):
    rejected = coordinator(tmp_path, Broker({"ErrorInfo": {"ErrorCode": "NotTradable"}}))
    with pytest.raises(PermissionError, match="precheck rejected"):
        rejected.preview(order(), ReconciliationResult(True, ()))
    service = coordinator(tmp_path)
    result = service.submit(order(), ReconciliationResult(True, ()), True)
    assert result.submitted
    with pytest.raises(PermissionError, match="Duplicate"):
        service.submit(order(), ReconciliationResult(True, ()), True)


def test_partial_fill_and_cancellation_are_persisted(tmp_path):
    broker = Broker(); service = coordinator(tmp_path, broker)
    service.submit(order(), ReconciliationResult(True, ()), True)
    assert service.record_status("botef-key", {"Status": "PartiallyFilled", "OrderId": "123"}) == "partially_filled"
    assert service.cancel("botef-key", "account", "123")["cancelled"]
    assert broker.cancelled == 1
