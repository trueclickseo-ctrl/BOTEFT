from quant_ai_trader.data.database import MarketDataRepository


def test_upsert_and_load_bars(tmp_path, sample_bars):
    repository = MarketDataRepository(tmp_path / "market.sqlite3")
    repository.initialize()
    assert repository.upsert_bars("spy", sample_bars.iloc[:5]) == 5
    updated = sample_bars.iloc[:5].copy()
    updated.iloc[0, updated.columns.get_loc("close")] = 999
    repository.upsert_bars("SPY", updated)
    loaded = repository.load_bars("SPY")
    assert len(loaded) == 5
    assert loaded.iloc[0]["close"] == 999
    assert repository.latest_bar_date("SPY") == sample_bars.index[4]

def test_capital_sleeve_preserves_only_its_own_equity(tmp_path):
    repository=MarketDataRepository(tmp_path / "market.sqlite3"); repository.initialize()
    assert repository.get_or_create_capital_sleeve("bot",10_000,"SEK")["current_capital"]==10_000
    assert repository.mark_capital_sleeve("bot",11_000)["current_capital"]==11_000
