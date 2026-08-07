"""Safe broker contract and Saxo OpenAPI v2 adapter."""
from dataclasses import dataclass
from typing import Protocol
import uuid
from quant_ai_trader.execution.safety import TradingSafety

@dataclass(frozen=True)
class OrderRequest:
    symbol: str; uic: int; asset_type: str; account_key: str; side: str; quantity: int; strategy: str; idempotency_key: str | None = None

class BrokerInterface(Protocol):
    def precheck(self, order: OrderRequest) -> dict: ...
    def place(self, order: OrderRequest) -> dict: ...

class SaxoBroker:
    def __init__(self, access_token: str, base_url: str, session=None, allow_submission: bool = False, environment: str = "sim", safety: TradingSafety | None = None):
        import requests
        self.session = session or requests.Session(); self.session.headers.update({"Authorization": f"Bearer {access_token}"})
        self.base_url, self.allow_submission, self.environment, self.safety = base_url.rstrip("/"), allow_submission, environment, safety or TradingSafety()
    def _payload(self, order: OrderRequest) -> dict:
        external_reference = order.idempotency_key or f"{order.strategy[:20]}-{uuid.uuid4().hex[:12]}"
        return {"AccountKey": order.account_key, "Uic": order.uic, "AssetType": order.asset_type, "BuySell": order.side, "Amount": order.quantity, "OrderType": "Market", "OrderDuration": {"DurationType": "DayOrder"}, "ExternalReference": external_reference[:50], "FieldGroups": ["Costs"], "ManualOrder": False}
    def precheck(self, order: OrderRequest) -> dict:
        response = self.session.post(f"{self.base_url}/trade/v2/orders/precheck", json=self._payload(order), timeout=30); response.raise_for_status(); return response.json()
    def place(self, order: OrderRequest) -> dict:
        if not self.allow_submission: raise PermissionError("Order submission disabled. Use simulation and explicit approval first.")
        self.safety.assert_order_allowed(self.environment)
        response = self.session.post(f"{self.base_url}/trade/v2/orders", json=self._payload(order), timeout=30); response.raise_for_status(); return response.json()
    def net_positions(self, account_key: str, client_key: str | None = None) -> dict:
        response = self.session.get(f"{self.base_url}/port/v1/netpositions", params={"ClientKey": client_key or account_key, "AccountKey": account_key, "$top": 100}, timeout=30)
        response.raise_for_status(); return response.json()
    def positions(self, account_key: str, client_key: str | None = None) -> dict:
        response = self.session.get(f"{self.base_url}/port/v1/positions", params={"ClientKey": client_key or account_key, "AccountKey": account_key, "FieldGroups": "DisplayAndFormat,PositionBase", "$top": 100}, timeout=30)
        response.raise_for_status(); return response.json()
    def accounts(self) -> dict:
        """Read simulation accounts only; this endpoint has no trading side effect."""
        response = self.session.get(f"{self.base_url}/port/v1/accounts/me", timeout=30)
        response.raise_for_status(); return response.json()
    def balances(self, account_key: str, client_key: str | None = None) -> dict:
        response = self.session.get(f"{self.base_url}/port/v1/balances", params={"ClientKey": client_key or account_key, "AccountKey": account_key}, timeout=30)
        response.raise_for_status(); return response.json()
    def open_orders(self, account_key: str, client_key: str | None = None) -> dict:
        response = self.session.get(f"{self.base_url}/port/v1/orders/me", params={"ClientKey": client_key or account_key, "AccountKey": account_key, "$top": 100}, timeout=30)
        response.raise_for_status(); return response.json()
    def instrument_details(self, uic: int, asset_type: str) -> dict:
        response = self.session.get(f"{self.base_url}/ref/v1/instruments/details/{uic}/{asset_type}", timeout=30)
        response.raise_for_status(); return response.json()
    def info_price(self, account_key: str, uic: int, asset_type: str, amount: int = 1) -> dict:
        """Return a non-tradable informational quote; this never creates an order."""
        response = self.session.get(f"{self.base_url}/trade/v1/infoprices", params={
            "AccountKey": account_key, "Uic": uic, "AssetType": asset_type, "Amount": amount,
            "FieldGroups": "DisplayAndFormat,InstrumentPriceDetails,PriceInfo,PriceInfoDetails,Quote",
        }, timeout=30)
        response.raise_for_status(); return response.json()
    def order_status(self, client_key: str, order_id: str) -> dict:
        response = self.session.get(f"{self.base_url}/port/v1/orders/{client_key}/{order_id}", timeout=30)
        response.raise_for_status(); return response.json()
    def cancel_order(self, account_key: str, order_id: str) -> dict:
        if not self.allow_submission: raise PermissionError("Order cancellation disabled with submission")
        self.safety.assert_order_allowed(self.environment)
        response = self.session.delete(f"{self.base_url}/trade/v2/orders/{order_id}", params={"AccountKey": account_key}, timeout=30)
        response.raise_for_status(); return response.json() if getattr(response, "content", b"") else {"cancelled": True}
