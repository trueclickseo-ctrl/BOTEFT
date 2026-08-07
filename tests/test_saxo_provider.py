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


class PaginatedResponse:
    def __init__(self, date): self.date = date
    def raise_for_status(self): return None
    def json(self):
        return {"Data": [{"Time": self.date, "Open": 100, "High": 102, "Low": 99, "Close": 101, "Volume": 1000}]}


class PaginatedSession:
    def __init__(self): self.headers, self.calls = {}, []
    def get(self, url, params, timeout):
        self.calls.append(params)
        return PaginatedResponse(params["Time"])


class InconsistentCandleResponse(FakeResponse):
    def json(self):
        return {"Data": [
            {"Time": "2024-01-02T00:00:00Z", "Open": 100, "High": 102, "Low": 101, "Close": 102, "Volume": 1000},
        ]}


class InconsistentCandleSession(FakeSession):
    def get(self, url, params, timeout):
        return InconsistentCandleResponse()


def test_saxo_provider_normalizes_chart_samples():
    provider = SaxoBankProvider("test-token", {"SPY": SaxoInstrument(42)}, "https://example.test/openapi", FakeSession())
    bars = provider.fetch_daily_bars("SPY", "2024-01-01", "2024-01-04")
    assert isinstance(bars.index, pd.DatetimeIndex)
    assert list(bars.columns) == ["open", "high", "low", "close", "volume", "adjusted_close"]
    assert bars.loc[pd.Timestamp("2024-01-03"), "adjusted_close"] == 102


def test_saxo_provider_paginates_multi_year_requests():
    session = PaginatedSession()
    provider = SaxoBankProvider("test-token", {"SPY": SaxoInstrument(42)}, "https://example.test/openapi", session)
    bars = provider.fetch_daily_bars("SPY", "2020-01-01", "2025-10-01")
    assert len(session.calls) == 3
    assert len(bars) == 3
    assert all(call["Count"] <= 1200 for call in session.calls)


def test_saxo_provider_expands_candle_range_to_include_open_and_close():
    provider = SaxoBankProvider("test-token", {"SPY": SaxoInstrument(42)}, "https://example.test/openapi", InconsistentCandleSession())
    bars = provider.fetch_daily_bars("SPY", "2024-01-01", "2024-01-03")
    assert bars.iloc[0]["low"] == 100
