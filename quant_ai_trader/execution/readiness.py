"""Fail-closed readiness checks before a strategy may enter paper trading."""
from __future__ import annotations
from dataclasses import dataclass
from quant_ai_trader.execution.reconciliation import ReconciliationResult
from quant_ai_trader.execution.safety import TradingSafety


@dataclass(frozen=True)
class PaperReadinessReport:
    ready: bool
    checks: dict[str, bool]
    blockers: tuple[str, ...]


def assess_paper_readiness(*, operator_approved: bool, account_key: str | None, environment: str, safety: TradingSafety, reconciliation: ReconciliationResult, allocation_translator_ready: bool) -> PaperReadinessReport:
    """Return all blockers; no implicit approval and no broker side effects."""
    safety_clear = True
    try:
        safety.assert_order_allowed(environment)
    except (PermissionError, ValueError):
        safety_clear = False
    checks = {
        "operator_approved": operator_approved,
        "simulation_environment": environment == "sim",
        "account_key_configured": bool(account_key),
        "kill_switch_inactive": safety_clear,
        "positions_reconciled": reconciliation.matched,
        "allocation_translator_ready": allocation_translator_ready,
    }
    labels = {
        "operator_approved": "operator approval required",
        "simulation_environment": "paper trading requires SAXO_ENVIRONMENT=sim",
        "account_key_configured": "SAXO_ACCOUNT_KEY is required",
        "kill_switch_inactive": "kill switch is active or environment is invalid",
        "positions_reconciled": "local and broker positions are not reconciled",
        "allocation_translator_ready": "candidate allocation-to-order translator is not implemented",
    }
    blockers = tuple(labels[key] for key, passed in checks.items() if not passed)
    return PaperReadinessReport(not blockers, checks, blockers)
