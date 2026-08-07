"""Read-only Saxo simulation account discovery for paper-readiness setup."""
from __future__ import annotations
from quant_ai_trader.config.settings import SaxoSettings
from quant_ai_trader.execution.broker_interface import SaxoBroker

def run() -> dict:
    settings=SaxoSettings.from_environment()
    if settings.environment != "sim": raise PermissionError("Account lookup is restricted to SAXO_ENVIRONMENT=sim")
    return SaxoBroker(settings.access_token,settings.base_url,environment="sim").accounts()

if __name__ == "__main__": print(run())
