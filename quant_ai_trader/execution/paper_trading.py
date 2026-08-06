"""Deterministic paper broker for validating the full order lifecycle."""
from dataclasses import dataclass
from datetime import UTC, datetime
from quant_ai_trader.execution.broker_interface import OrderRequest

@dataclass
class PaperBroker:
    enabled: bool = True
    def precheck(self, order: OrderRequest) -> dict:
        return {"approved": self.enabled and order.quantity > 0 and order.side in {"Buy", "Sell"}}
    def place(self, order: OrderRequest) -> dict:
        if not self.precheck(order)["approved"]: raise PermissionError("Paper order rejected by safety controls")
        return {"OrderId": f"paper-{datetime.now(UTC).timestamp():.0f}", "status": "Filled", "symbol": order.symbol, "quantity": order.quantity}
