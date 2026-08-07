"""Fail-closed order lifecycle coordination around the Saxo adapter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from quant_ai_trader.execution.broker_interface import OrderRequest, SaxoBroker
from quant_ai_trader.execution.idempotency import OrderIntentLedger
from quant_ai_trader.execution.reconciliation import ReconciliationResult
from quant_ai_trader.operations.strategy_approval import assert_paper_approved


@dataclass(frozen=True)
class SubmissionResult:
    submitted: bool
    response: dict


class ExecutionCoordinator:
    def __init__(self, broker: SaxoBroker, ledger: OrderIntentLedger,
                 approval_check: Callable[[str], None] = assert_paper_approved) -> None:
        self.broker, self.ledger, self.approval_check = broker, ledger, approval_check

    def preview(self, order: OrderRequest, reconciliation: ReconciliationResult) -> dict:
        self.approval_check(order.strategy)
        if not reconciliation.matched:
            raise PermissionError("Broker and local positions are not reconciled")
        response = self.broker.precheck(order)
        if response.get("ErrorInfo"):
            raise PermissionError(f"Saxo precheck rejected order: {response['ErrorInfo']}")
        return response

    def submit(self, order: OrderRequest, reconciliation: ReconciliationResult,
               operator_approved: bool) -> SubmissionResult:
        if not operator_approved:
            raise PermissionError("Explicit operator approval is required")
        if not order.idempotency_key:
            raise ValueError("Order idempotency_key is required")
        precheck = self.preview(order, reconciliation)
        if not self.ledger.reserve(order.idempotency_key):
            raise PermissionError("Duplicate order intent blocked")
        try:
            response = self.broker.place(order)
        except Exception:
            self.ledger.mark(order.idempotency_key, "submission_failed")
            raise
        order_id = response.get("OrderId")
        self.ledger.mark(order.idempotency_key, "submitted", str(order_id) if order_id else None)
        return SubmissionResult(True, {"precheck": precheck, "submission": response})

    def record_status(self, idempotency_key: str, payload: dict) -> str:
        status = str(payload.get("Status", "unknown")).lower()
        normalized = {"partiallyfilled": "partially_filled", "filled": "filled",
                      "cancelled": "cancelled", "rejected": "rejected"}.get(status, status)
        self.ledger.mark(idempotency_key, normalized, str(payload.get("OrderId")) if payload.get("OrderId") else None)
        return normalized

    def cancel(self, idempotency_key: str, account_key: str, order_id: str) -> dict:
        response = self.broker.cancel_order(account_key, order_id)
        self.ledger.mark(idempotency_key, "cancelled", order_id)
        return response
