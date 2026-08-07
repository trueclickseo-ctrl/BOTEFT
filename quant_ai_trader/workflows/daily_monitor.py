"""Daily research-only monitor: sync data and reassess the fixed QQQ candidate."""
from __future__ import annotations
from datetime import date, timedelta
from quant_ai_trader.config.settings import SaxoSettings, Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.data.market_data import SaxoBankProvider, SaxoInstrument, sync_symbol
from quant_ai_trader.observability.logging import configure_logging
from quant_ai_trader.workflows.breakout_walkforward import run as validate_breakout

def run(symbols: list[str], candidate_symbol: str = "QQQ") -> dict:
    settings, saxo = Settings(), SaxoSettings.from_environment()
    repo = MarketDataRepository(settings.database_path); repo.initialize()
    instruments = {name: SaxoInstrument(**details) for name, details in saxo.instruments.items()}
    provider = SaxoBankProvider(saxo.access_token, instruments, saxo.base_url)
    # End is exclusive. Using today's date prevents an in-progress daily bar
    # from entering research or driving a decision during the market session.
    end = date.today().isoformat()
    updated = {}
    for symbol in symbols:
        latest = repo.latest_bar_date(symbol)
        start = (latest + timedelta(days=1)).isoformat() if latest else "2021-08-01"
        if start >= end:
            updated[symbol] = 0
            continue
        try:
            updated[symbol] = sync_symbol(provider, repo, symbol, start, end)
        except ValueError as error:
            if "No chart samples returned" not in str(error): raise
            updated[symbol] = 0
    validation = validate_breakout(candidate_symbol)
    configure_logging().info("daily_research_monitor", extra={"strategy": "atr_breakout_v1", "event": str(validation)})
    return {"updated_bars": updated, "breakout_validation": validation}
