from quant_ai_trader.execution.broker_interface import SaxoBroker

class Response:
    def raise_for_status(self): pass
    def json(self): return {"Data":[{"AccountKey":"sim-key"}]}
class Session:
    def __init__(self): self.headers={}
    def get(self,url,**kwargs):
        assert url.endswith("/port/v1/accounts/me"); return Response()

def test_saxo_accounts_is_read_only():
    assert SaxoBroker("token","https://example.test/openapi",session=Session()).accounts()["Data"][0]["AccountKey"]=="sim-key"
