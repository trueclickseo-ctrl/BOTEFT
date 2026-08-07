# BOTEF market-data conventions

BOTEF keeps research and execution data separate.

## Saxo execution data

- Database: `data/quant_ai_trader.sqlite3`
- Source: Saxo OpenAPI daily chart endpoint
- Purpose: broker-aligned monitoring, quotes, signals, and execution checks
- Convention: price-only; `adjusted_close` equals `close`
- Limitation: dividends, distributions, splits, and other corporate-action adjustments are not supplied as a total-return series

## Adjusted research data

- Database: `data/adjusted_total_return.sqlite3`
- Source: Yahoo Finance through the isolated `YahooFinanceProvider`
- Purpose: historical strategy research involving ETF returns
- Convention: raw OHLC plus provider-supplied adjusted close
- Frozen download: 2014-01-01 through 2026-08-08 (end exclusive)
- Universe: SPY, QQQ, IWM, DIA, XLK, XLF, XLE, XLV, XLI, XLY, XLP, TLT, GLD, SLV, IEF, TIP, PDBC, EFA, EEM, VNQ

Yahoo data is suitable for research but is not the broker execution record and carries no service-level guarantee. A future paid total-return feed may replace it. Strategies must never mix Saxo price-only series and Yahoo adjusted series within one cross-sectional run.
