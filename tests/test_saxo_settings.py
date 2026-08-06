from quant_ai_trader.config.settings import SaxoSettings

def test_saxo_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("SAXO_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("SAXO_INSTRUMENTS_JSON", '{"SPY":{"uic":36590,"asset_type":"Etf"}}')
    assert SaxoSettings.from_environment().instruments["SPY"]["uic"] == 36590
