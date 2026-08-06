"""Version-controlled investable-universe metadata."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Instrument:
    symbol: str
    sector: str
    asset_type: str = "Etf"

ETF_UNIVERSE = (
    Instrument("SPY", "Broad Market"), Instrument("QQQ", "Technology"), Instrument("IWM", "Small Cap"), Instrument("DIA", "Broad Market"),
    Instrument("XLK", "Technology"), Instrument("XLF", "Financials"), Instrument("XLE", "Energy"), Instrument("XLV", "Health Care"),
    Instrument("XLI", "Industrials"), Instrument("XLY", "Consumer Discretionary"), Instrument("XLP", "Consumer Staples"),
    Instrument("TLT", "Treasury Bonds"), Instrument("GLD", "Precious Metals"), Instrument("SLV", "Precious Metals"),
)

LARGE_CAP_UNIVERSE = (
    Instrument("AAPL", "Technology", "Stock"), Instrument("MSFT", "Technology", "Stock"), Instrument("NVDA", "Technology", "Stock"),
    Instrument("AMZN", "Consumer Discretionary", "Stock"), Instrument("GOOGL", "Communication Services", "Stock"), Instrument("META", "Communication Services", "Stock"),
    Instrument("JPM", "Financials", "Stock"), Instrument("JNJ", "Health Care", "Stock"), Instrument("XOM", "Energy", "Stock"),
)

def sector_for(symbol: str) -> str:
    for instrument in ETF_UNIVERSE + LARGE_CAP_UNIVERSE:
        if instrument.symbol == symbol.upper(): return instrument.sector
    raise KeyError(f"No sector metadata for {symbol}")
