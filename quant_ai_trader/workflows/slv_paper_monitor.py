"""One-command daily monitor for the non-submitting SLV paper pilot."""
from __future__ import annotations
from quant_ai_trader.observability.logging import configure_logging
from quant_ai_trader.workflows.daily_monitor import run as refresh_and_validate
from quant_ai_trader.workflows.paper_readiness import run as paper_readiness
from quant_ai_trader.workflows.slv_paper_pilot import run as paper_pilot


def run() -> dict[str, object]:
    refresh = refresh_and_validate(["SPY", "SLV"], candidate_symbol="SLV")
    pilot, readiness = paper_pilot(), paper_readiness()
    result = {"refresh": refresh["updated_bars"], "validation": refresh["breakout_validation"], "pilot": pilot, "paper_readiness": readiness}
    configure_logging().info("slv_paper_pilot_monitor", extra={"strategy":"atr_breakout_v1_slv", "event":str({"decision":pilot["decision"], "ready":readiness["ready"]})})
    return result


if __name__ == "__main__":
    print(run())
