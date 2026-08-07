"""Daily-bar event-driven backtester with conservative intraday execution assumptions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_ai_trader.backtesting.performance import calculate_performance
from quant_ai_trader.strategies.etf_strategy import StrategyRules


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 100_000.0
    risk_per_trade: float = 0.01
    maximum_allocation: float = 0.10
    commission_per_share: float = 0.005
    slippage_bps: float = 2.0
    minimum_commission: float = 0.0
    commission_bps: float = 0.0
    fx_conversion_bps: float = 0.0

    @classmethod
    def saxo_us_etf_eur(cls, *, stress_multiplier: float = 1.0) -> "BacktestConfig":
        """Published Saxo Classic US-ETF pricing plus conservative execution costs."""
        return cls(
            commission_per_share=0.0,
            minimum_commission=1.0 * stress_multiplier,
            commission_bps=8.0 * stress_multiplier,
            slippage_bps=5.0 * stress_multiplier,
            fx_conversion_bps=25.0 * stress_multiplier,
        )


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.Series
    trades: pd.DataFrame
    metrics: dict[str, float]


class ETFBacktester:
    """Long-only daily-bar backtester.

    Signals are generated at a day's close and filled at the next open. If a bar reaches
    both target and stop, the stop is filled to avoid optimistic intraday assumptions.
    """

    def __init__(self, rules: StrategyRules = StrategyRules(), config: BacktestConfig = BacktestConfig()) -> None:
        self.rules, self.config = rules, config

    def run(self, bars: pd.DataFrame, signals: pd.DataFrame) -> BacktestResult:
        required_bars = {"open", "high", "low", "close"}
        missing_bars = required_bars - set(bars.columns)
        required_signals = {"entry_signal", "exit_signal"}
        missing_signals = required_signals - set(signals.columns)
        if missing_bars or missing_signals:
            raise ValueError(f"Missing bars: {sorted(missing_bars)}; missing signals: {sorted(missing_signals)}")
        data = bars.join(signals, how="left").sort_index()
        data[["entry_signal", "exit_signal"]] = data[["entry_signal", "exit_signal"]].fillna(False).astype(bool)
        cash, position, entry = self.config.initial_cash, None, None
        equity_values: list[float] = []
        closed_trades: list[dict[str, object]] = []

        for row_number, (timestamp, row) in enumerate(data.iterrows()):
            # A signal at yesterday's close fills at today's open.
            if position is None and row_number > 0 and bool(data.iloc[row_number - 1]["entry_signal"]):
                prior = data.iloc[row_number - 1]
                entry = self._open_position(timestamp, float(row["open"]), cash, prior.get("stop_loss_fraction"), prior.get("target_return_fraction"))
                if entry is not None:
                    cash -= entry["entry_cost"]
                    position = entry

            if position is not None:
                exit_reason, raw_exit = self._exit_price(row, position)
                if exit_reason is not None:
                    cash, trade = self._close_position(timestamp, position, raw_exit, exit_reason, cash)
                    closed_trades.append(trade)
                    position = None

            marked_position = 0.0 if position is None else position["shares"] * float(row["close"])
            equity_values.append(cash + marked_position)

        # Close any remaining position at the final close; it cannot remain open in results.
        if position is not None:
            final_time, final_row = data.index[-1], data.iloc[-1]
            cash, trade = self._close_position(final_time, position, float(final_row["close"]), "end_of_data", cash)
            closed_trades.append(trade)
            equity_values[-1] = cash

        equity_curve = pd.Series(equity_values, index=data.index, name="equity")
        trades = pd.DataFrame(closed_trades)
        metrics = calculate_performance(equity_curve, trades)
        return BacktestResult(equity_curve, trades, metrics)

    def _open_position(self, timestamp: pd.Timestamp, raw_price: float, cash: float, stop_override=None, target_override=None) -> dict[str, object] | None:
        entry_price = raw_price * (1 + self.config.slippage_bps / 10_000)
        stop_loss = float(stop_override) if pd.notna(stop_override) else self.rules.stop_loss
        target_return = float(target_override) if pd.notna(target_override) else self.rules.target_return
        stop_price = entry_price * (1 - stop_loss)
        risk_per_share = entry_price - stop_price
        allocation_cap = min(cash, self.config.initial_cash) * self.config.maximum_allocation
        risk_cap = self.config.initial_cash * self.config.risk_per_trade
        shares = int(min(risk_cap / risk_per_share, allocation_cap / entry_price))
        if shares < 1:
            return None
        notional = shares * entry_price
        commission, fx_cost = self._transaction_cost(notional, shares)
        return {
            "entry_time": timestamp, "entry_price": entry_price, "stop_price": stop_price,
            "target_price": entry_price * (1 + target_return), "shares": shares,
            "entry_commission": commission, "entry_fx_cost": fx_cost,
            "entry_cost": notional + commission + fx_cost, "days_held": 0,
        }

    def _exit_price(self, row: pd.Series, position: dict[str, object]) -> tuple[str | None, float | None]:
        position["days_held"] = int(position["days_held"]) + 1
        hit_stop = float(row["low"]) <= float(position["stop_price"])
        hit_target = float(row["high"]) >= float(position["target_price"])
        if hit_stop:
            return "stop_loss", float(position["stop_price"])
        if hit_target:
            return "profit_target", float(position["target_price"])
        if bool(row["exit_signal"]):
            return "probability_exit", float(row["close"])
        if int(position["days_held"]) >= self.rules.maximum_holding_days:
            return "maximum_holding_period", float(row["close"])
        return None, None

    def _close_position(self, timestamp: pd.Timestamp, position: dict[str, object], raw_price: float, reason: str, cash: float) -> tuple[float, dict[str, object]]:
        exit_price = raw_price * (1 - self.config.slippage_bps / 10_000)
        shares = int(position["shares"])
        notional = shares * exit_price
        exit_commission, exit_fx_cost = self._transaction_cost(notional, shares)
        proceeds = notional - exit_commission - exit_fx_cost
        net_pnl = proceeds - float(position["entry_cost"])
        trade = {
            "entry_time": position["entry_time"], "exit_time": timestamp, "entry_price": position["entry_price"],
            "exit_price": exit_price, "shares": shares, "days_held": position["days_held"], "exit_reason": reason,
            "entry_commission": position["entry_commission"], "exit_commission": exit_commission, "net_pnl": net_pnl,
            "entry_fx_cost": position.get("entry_fx_cost", 0.0), "exit_fx_cost": exit_fx_cost,
            "total_cost": float(position["entry_commission"]) + float(position.get("entry_fx_cost", 0.0)) + exit_commission + exit_fx_cost,
            "return_pct": net_pnl / float(position["entry_cost"]),
        }
        return cash + proceeds, trade

    def _transaction_cost(self, notional: float, shares: int) -> tuple[float, float]:
        commission = max(
            shares * self.config.commission_per_share,
            self.config.minimum_commission,
            notional * self.config.commission_bps / 10_000,
        )
        fx_cost = notional * self.config.fx_conversion_bps / 10_000
        return float(commission), float(fx_cost)
