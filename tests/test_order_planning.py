from datetime import UTC, datetime, timedelta

from quant_ai_trader.execution.idempotency import OrderIntentLedger
from quant_ai_trader.execution.order_planning import translate_target_weights


def test_allocation_translation_rounds_down_and_is_deterministic():
    now = datetime(2026, 8, 7, 14, tzinfo=UTC)
    kwargs = dict(weights={"SPY": .10, "CASH": .90}, prices={"SPY": 101.0}, current_quantities={},
                  instruments={"SPY": {"uic": 42, "asset_type": "Etf"}}, sectors={"SPY": "Broad"},
                  equity=10_000, account_key="account", strategy="approved", price_as_of=now, now=now)
    first, second = translate_target_weights(**kwargs), translate_target_weights(**kwargs)
    assert first.approved and first.orders[0].quantity == 9
    assert first.orders[0].idempotency_key == second.orders[0].idempotency_key
    assert first.residual_cash == 9091


def test_translation_rejects_stale_prices_and_limit_breaches():
    now = datetime(2026, 8, 7, 14, tzinfo=UTC)
    plan = translate_target_weights(weights={"SPY": .20}, prices={"SPY": 100}, current_quantities={},
        instruments={"SPY": {"uic": 42}}, sectors={"SPY": "Broad"}, equity=10_000,
        account_key="account", strategy="test", price_as_of=now-timedelta(hours=1), now=now)
    assert not plan.approved
    assert "SPY: maximum ETF allocation exceeded" in plan.blockers
    assert "market prices are stale" in plan.blockers


def test_order_intent_ledger_blocks_duplicate_restart(tmp_path):
    ledger = OrderIntentLedger(tmp_path / "intents.json")
    assert ledger.reserve("same-order")
    assert not OrderIntentLedger(tmp_path / "intents.json").reserve("same-order")
    ledger.mark("same-order", "filled", "123")
