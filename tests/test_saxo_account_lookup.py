from quant_ai_trader.execution.broker_interface import SaxoBroker

class Response:
    def raise_for_status(self): pass
    def json(self): return {"Data":[{"AccountKey":"sim-key"}]}
class Session:
    def __init__(self): self.headers={}; self.urls=[]
    def get(self,url,**kwargs):
        self.urls.append((url, kwargs)); return Response()

def test_saxo_accounts_is_read_only():
    assert SaxoBroker("token","https://example.test/openapi",session=Session()).accounts()["Data"][0]["AccountKey"]=="sim-key"


def test_saxo_read_only_portfolio_and_reference_endpoints():
    session = Session()
    broker = SaxoBroker("token", "https://example.test/openapi", session=session)
    broker.balances("account")
    broker.net_positions("account")
    broker.open_orders("account")
    broker.instrument_details(42, "Etf")
    broker.info_price("account", 42, "Etf")
    assert [url.rsplit("/openapi", 1)[-1] for url, _ in session.urls] == [
        "/port/v1/balances", "/port/v1/netpositions", "/port/v1/orders/me",
        "/ref/v1/instruments/details/42/Etf", "/trade/v1/infoprices",
    ]
    assert all("post" not in url for url, _ in session.urls)
