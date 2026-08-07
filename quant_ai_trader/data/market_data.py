"""Market-data provider interface and Yahoo Finance implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from quant_ai_trader.data.database import REQUIRED_COLUMNS


class MarketDataProvider(Protocol):
    def fetch_daily_bars(self, symbol: str, start: str, end: str) -> pd.DataFrame: ...


class YahooFinanceProvider:
    """Download adjusted daily OHLCV data with yfinance.

    The provider is intentionally isolated so a paid or broker data feed can replace it later.
    """

    def fetch_daily_bars(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        import yfinance as yf

        raw = yf.download(symbol, start=start, end=end, interval="1d", auto_adjust=False, progress=False)
        if raw.empty:
            raise ValueError(f"No daily bars returned for {symbol} between {start} and {end}")
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        renamed = raw.rename(columns={
            "Open": "open", "High": "high", "Low": "low", "Close": "close",
            "Volume": "volume", "Adj Close": "adjusted_close",
        })
        missing = set(REQUIRED_COLUMNS) - set(renamed.columns)
        if missing:
            raise ValueError(f"Provider response missing columns: {sorted(missing)}")
        return renamed.loc[:, REQUIRED_COLUMNS].sort_index()


@dataclass(frozen=True)
class SaxoInstrument:
    """A Saxo instrument identifier; symbols alone are insufficient for OpenAPI."""

    uic: int
    asset_type: str = "Etf"


class SaxoBankProvider:
    """Daily OHLCV provider backed by Saxo OpenAPI chart data.

    Saxo identifies products by UIC and AssetType, so approved instruments must be mapped
    explicitly. Access tokens are supplied at runtime and are never persisted by this class.
    """

    def __init__(self, access_token: str, instruments: dict[str, SaxoInstrument], base_url: str, session: Any = None) -> None:
        if not access_token:
            raise ValueError("A Saxo OpenAPI access token is required")
        self.instruments = {symbol.upper(): instrument for symbol, instrument in instruments.items()}
        self.base_url = base_url.rstrip("/")
        if session is None:
            import requests
            session = requests.Session()
        self.session = session
        self.session.headers.update({"Authorization": f"Bearer {access_token}", "Accept": "application/json"})

    def fetch_daily_bars(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        instrument = self.instruments.get(symbol.upper())
        if instrument is None:
            raise ValueError(f"No Saxo UIC/AssetType mapping configured for {symbol}")
        start_time, end_time = pd.Timestamp(start), pd.Timestamp(end)
        if start_time >= end_time:
            raise ValueError("Start date must be earlier than end date")
        # Saxo's chart endpoint caps Count at 1,200. Use calendar windows below
        # that limit so a multi-year research request is never silently truncated.
        windows: list[pd.DataFrame] = []
        cursor = start_time
        while cursor < end_time:
            window_end = min(cursor + pd.DateOffset(days=1000), end_time)
            samples = self._fetch_chart_window(instrument, cursor, window_end)
            if samples:
                windows.append(pd.DataFrame(samples))
            cursor = window_end
        if not windows:
            raise ValueError(f"No chart samples returned by Saxo for {symbol}")
        bars = pd.concat(windows, ignore_index=True)
        rename_map = {"Time": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
        missing = set(rename_map) - set(bars.columns)
        if missing:
            raise ValueError(f"Saxo chart response missing columns: {sorted(missing)}")
        bars = bars.rename(columns=rename_map).loc[:, ["date", "open", "high", "low", "close", "volume"]]
        bars["date"] = pd.to_datetime(bars["date"], utc=True).dt.tz_localize(None)
        bars = bars.set_index("date").sort_index().loc[lambda frame: ~frame.index.duplicated(keep="last")]
        bars = bars.loc[(bars.index >= start_time) & (bars.index < end_time)]
        # Chart data is unadjusted. Corporate-action adjustment is a dedicated future
        # pipeline; retaining this explicitly avoids silently claiming adjusted history.
        bars["adjusted_close"] = bars["close"]
        return bars.loc[:, REQUIRED_COLUMNS]

    def _fetch_chart_window(self, instrument: SaxoInstrument, start_time: pd.Timestamp, end_time: pd.Timestamp) -> list[dict[str, Any]]:
        requested_days = max((end_time - start_time).days, 1)
        response = self.session.get(
            f"{self.base_url}/chart/v3/charts",
            params={
                "Uic": instrument.uic, "AssetType": instrument.asset_type, "Horizon": 1440,
                "Mode": "From", "Time": start_time.strftime("%Y-%m-%dT00:00:00Z"),
                "Count": min(max(requested_days + 15, 100), 1200),
            }, timeout=30,
        )
        response.raise_for_status()
        return response.json().get("Data", [])


def sync_symbol(provider: MarketDataProvider, repository: object, symbol: str, start: str, end: str) -> int:
    """Fetch a symbol and persist it. Repository supports ``upsert_bars``."""
    bars = provider.fetch_daily_bars(symbol, start, end)
    return repository.upsert_bars(symbol, bars)
