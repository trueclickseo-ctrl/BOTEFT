import pandas as pd

from quant_ai_trader.data.market_data import SaxoBankProvider, SaxoInstrument


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"Data": [
            {"Time": "2024-01-02T00:00:00Z", "Open": 100, "High": 102, "Low": 99, "Close": 101, "Volume": 1000},
            {"Time": "2024-01-03T00:00:00Z", "Open": 101, "High": 103, "Low": 100, "Close": 102, "Volume": 1200},
        ]}


class FakeSession:
    def __init__(self):
        self.headers = {}

    def get(self, url, params, timeout):
        assert url.endswith("/chart/v3/charts")
        assert params["Uic"] == 42
        assert params["AssetType"] == "Etf"
        return FakeResponse()


def test_saxo_provider_normalizes_chart_samples():
    provider = SaxoBankProvider("test-token", {"SPY": SaxoInstrument(42)}, "https://example.test/openapi", FakeSession())
    bars = provider.fetch_daily_bars("SPY", "2024-01-01", "2024-01-04")
    assert isinstance(bars.index, pd.DatetimeIndex)
    assert list(bars.columns) == ["open", "high", "low", "close", "volume", "adjusted_close"]
    assert bars.loc[pd.Timestamp("2024-01-03"), "adjusted_close"] == 102
