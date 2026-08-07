"""Download expanded stock universes into their separate research database."""
from pathlib import Path
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.data.market_data import YahooFinanceProvider
from quant_ai_trader.workflows.stocks.large_universes import NASDAQ_100, SP_500_TOP_50

DATABASE=Path("data/stocks/large_universes.sqlite3")

def run(end="2026-08-09"):
    repo=MarketDataRepository(DATABASE); repo.initialize(); provider=YahooFinanceProvider(); failures={}; coverage={}
    for symbol in sorted(set(NASDAQ_100)|set(SP_500_TOP_50)|{"SPY"}):
        try:
            bars=provider.fetch_daily_bars(symbol,"2014-01-01",end); repo.upsert_bars(symbol,bars)
            coverage[symbol]=(len(bars),str(bars.index[0].date()),str(bars.index[-1].date()))
        except Exception as error: failures[symbol]=str(error)
    return {"coverage":coverage,"failures":failures}

if __name__=="__main__":
    result=run(); print({"downloaded":len(result["coverage"]),"failures":result["failures"]})
