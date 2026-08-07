"""Run a non-mutating, fail-closed paper-trading readiness preflight."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from quant_ai_trader.execution.readiness import assess_paper_readiness
from quant_ai_trader.execution.reconciliation import ReconciliationResult
from quant_ai_trader.execution.safety import TradingSafety


def run(operator_approved: bool = False, broker_positions_json: str = "{}") -> dict[str, object]:
    # Broker positions must be fetched and reconciled by the future Saxo portfolio
    # adapter; accepting no positions is not treated as a reconciliation approval.
    load_dotenv(dotenv_path=Path(".env"))
    try:
        broker_positions = json.loads(broker_positions_json)
    except json.JSONDecodeError as error:
        raise ValueError("broker_positions_json must be valid JSON") from error
    if not isinstance(broker_positions, dict):
        raise ValueError("broker_positions_json must be a JSON object")
    reconciliation = ReconciliationResult(matched=False, differences=("broker position reconciliation has not been executed",))
    report = assess_paper_readiness(
        operator_approved=operator_approved,
        account_key=os.getenv("SAXO_ACCOUNT_KEY"),
        environment=os.getenv("SAXO_ENVIRONMENT", "sim").lower(),
        safety=TradingSafety(), reconciliation=reconciliation,
        allocation_translator_ready=False,
    )
    return {"ready": report.ready, "checks": report.checks, "blockers": list(report.blockers), "broker_positions_received": len(broker_positions)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--operator-approved", action="store_true"); parser.add_argument("--broker-positions-json", default="{}")
    args = parser.parse_args(); print(run(args.operator_approved, args.broker_positions_json))
