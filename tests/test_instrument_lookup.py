from quant_ai_trader.config.settings import SaxoSettings
from quant_ai_trader.data.instrument_lookup import lookup

def test_lookup_prefers_exact_us_listing(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"Data": [{"Identifier": 2, "AssetType": "Etf", "Symbol": "QQQ:xetr"}, {"Identifier": 1, "AssetType": "Etf", "Symbol": "QQQ:xnas"}]}
    class Session:
        headers = {}
        def get(self, *args, **kwargs): return Response()
    monkeypatch.setattr("quant_ai_trader.data.instrument_lookup.requests.Session", lambda: Session())
    result = lookup(["QQQ"], SaxoSettings("token"))
    assert result["QQQ"]["uic"] == 1
