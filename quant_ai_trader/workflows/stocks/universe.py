"""Predeclared US blue-chip stock research universe, frozen before testing."""

# Current DJIA constituents as of the 2026-08-07 research freeze. Using current
# membership across older history introduces survivorship bias; this universe is
# suitable only for candidate discovery, never same-sample approval.
US_STOCK_UNIVERSE = (
    "MMM", "AXP", "AMGN", "AMZN", "AAPL", "BA", "CAT", "CVX", "CSCO", "KO",
    "DIS", "GOOGL", "GS", "HD", "HON", "IBM", "JNJ", "JPM", "MCD", "MRK",
    "MSFT", "NKE", "NVDA", "PG", "CRM", "SHW", "TRV", "UNH", "V", "WMT",
)

BENCHMARK_SYMBOL = "SPY"
HISTORY_START = "2014-01-01"
FORWARD_FREEZE_DATE = "2026-08-08"
