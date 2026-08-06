"""Safe broker contract and Saxo OpenAPI v2 adapter."""
from dataclasses import dataclass
from typing import Protocol
import uuid
from quant_ai_trader.execution.safety import TradingSafety

@dataclass(frozen=True)
class OrderRequest:
    symbol: str; uic: int; asset_type: str; account_key: str; side: str; quantity: int; strategy: str

class BrokerInterface(Protocol):
    def precheck(self, order: OrderRequest) -> dict: ...
    def place(self, order: OrderRequest) -> dict: ...

class SaxoBroker:
    def __init__(self, access_token: str, base_url: str, session=None, allow_submission: bool = False, environment: str = "sim", safety: TradingSafety | None = None):
        import requests
        self.session = session or requests.Session(); self.session.headers.update({"Authorization": f"Bearer {access_token}"})
        self.base_url, self.allow_submission, self.environment, self.safety = base_url.rstrip("/"), allow_submission, environment, safety or TradingSafety()
    def _payload(self, order: OrderRequest) -> dict:
        return {"AccountKey": order.account_key, "Uic": order.uic, "AssetType": order.asset_type, "BuySell": order.side, "Amount": order.quantity, "OrderType": "Market", "OrderDuration": {"DurationType": "DayOrder"}, "ExternalReference": f"{order.strategy[:20]}-{uuid.uuid4().hex[:12]}"}
    def precheck(self, order: OrderRequest) -> dict:
        response = self.session.post(f"{self.base_url}/trade/v2/orders/precheck", json=self._payload(order), timeout=30); response.raise_for_status(); return response.json()
    def place(self, order: OrderRequest) -> dict:
        if not self.allow_submission: raise PermissionError("Order submission disabled. Use simulation and explicit approval first.")
        self.safety.assert_order_allowed(self.environment)
        response = self.session.post(f"{self.base_url}/trade/v2/orders", json=self._payload(order), timeout=30); response.raise_for_status(); return response.json()
    def net_positions(self, account_key: str) -> dict:
        response = self.session.get(f"{self.base_url}/port/v1/netpositions", params={"AccountKey": account_key, "$top": 100}, timeout=30)
        response.raise_for_status(); return response.json()
