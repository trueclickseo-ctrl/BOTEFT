from unittest.mock import patch
from quant_ai_trader.workflows.slv_paper_monitor import run

def test_slv_monitor_is_non_submitting():
    with patch("quant_ai_trader.workflows.slv_paper_monitor.refresh_and_validate", return_value={"updated_bars":{"SPY":0,"SLV":0},"breakout_validation":{}}), patch("quant_ai_trader.workflows.slv_paper_monitor.paper_pilot", return_value={"decision":"NO_TRADE","orders_created":False}), patch("quant_ai_trader.workflows.slv_paper_monitor.paper_readiness", return_value={"ready":False}):
        result=run()
    assert result["pilot"]["orders_created"] is False and result["paper_readiness"]["ready"] is False
