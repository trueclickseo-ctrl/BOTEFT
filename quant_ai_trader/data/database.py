"""SQLite persistence for normalized daily OHLCV market data."""

from __future__ import annotations

import sqlite3
import json
from contextlib import closing
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume", "adjusted_close")


class MarketDataRepository:
    """Stores daily bars idempotently using a symbol/date primary key."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_bars (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    adjusted_close REAL NOT NULL,
                    PRIMARY KEY (symbol, date)
                )
                """
            )
            connection.execute("""CREATE TABLE IF NOT EXISTS strategy_runs (
                run_id TEXT PRIMARY KEY, strategy_name TEXT NOT NULL, symbol TEXT NOT NULL,
                completed_at TEXT NOT NULL, metrics_json TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS capital_sleeves (
                sleeve_name TEXT PRIMARY KEY, currency TEXT NOT NULL,
                initial_capital REAL NOT NULL, current_capital REAL NOT NULL
            )""")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_daily_bars_symbol_date ON daily_bars(symbol, date)"
            )

    def upsert_bars(self, symbol: str, bars: pd.DataFrame) -> int:
        """Insert or update bars. The input index must be a DatetimeIndex."""
        self._validate_bars(bars)
        normalized = bars.loc[:, REQUIRED_COLUMNS].copy()
        normalized.index = pd.to_datetime(normalized.index).tz_localize(None)
        rows = [
            (symbol.upper(), index.strftime("%Y-%m-%d"), *map(float, row))
            for index, row in normalized.iterrows()
        ]
        if not rows:
            return 0
        with closing(self._connect()) as connection, connection:
            connection.executemany(
                """
                INSERT INTO daily_bars (symbol, date, open, high, low, close, volume, adjusted_close)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, date) DO UPDATE SET
                    open=excluded.open, high=excluded.high, low=excluded.low,
                    close=excluded.close, volume=excluded.volume,
                    adjusted_close=excluded.adjusted_close
                """,
                rows,
            )
        return len(rows)

    def load_bars(self, symbol: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
        query = "SELECT date, open, high, low, close, volume, adjusted_close FROM daily_bars WHERE symbol = ?"
        parameters: list[str] = [symbol.upper()]
        if start:
            query += " AND date >= ?"
            parameters.append(str(pd.Timestamp(start).date()))
        if end:
            query += " AND date <= ?"
            parameters.append(str(pd.Timestamp(end).date()))
        query += " ORDER BY date"
        with closing(self._connect()) as connection:
            frame = pd.read_sql_query(query, connection, params=parameters, parse_dates=["date"])
        return frame.set_index("date") if not frame.empty else pd.DataFrame(columns=REQUIRED_COLUMNS)

    def list_symbols(self) -> list[str]:
        with closing(self._connect()) as connection:
            rows = connection.execute("SELECT DISTINCT symbol FROM daily_bars ORDER BY symbol").fetchall()
        return [row[0] for row in rows]

    def latest_bar_date(self, symbol: str) -> pd.Timestamp | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT MAX(date) FROM daily_bars WHERE symbol = ?", (symbol.upper(),)).fetchone()
        return pd.Timestamp(row[0]) if row and row[0] else None

    def get_or_create_capital_sleeve(self, sleeve_name: str, initial_capital: float, currency: str = "SEK") -> dict[str, object]:
        if initial_capital <= 0: raise ValueError("initial_capital must be positive")
        with closing(self._connect()) as connection, connection:
            connection.execute("INSERT OR IGNORE INTO capital_sleeves VALUES (?, ?, ?, ?)", (sleeve_name, currency.upper(), initial_capital, initial_capital))
            row = connection.execute("SELECT sleeve_name, currency, initial_capital, current_capital FROM capital_sleeves WHERE sleeve_name = ?", (sleeve_name,)).fetchone()
        return {"sleeve_name":row[0], "currency":row[1], "initial_capital":float(row[2]), "current_capital":float(row[3])}

    def mark_capital_sleeve(self, sleeve_name: str, current_capital: float) -> dict[str, object]:
        if current_capital < 0: raise ValueError("current_capital cannot be negative")
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute("UPDATE capital_sleeves SET current_capital = ? WHERE sleeve_name = ?", (current_capital, sleeve_name))
        if not cursor.rowcount: raise ValueError(f"Unknown capital sleeve: {sleeve_name}")
        return self.get_or_create_capital_sleeve(sleeve_name, 1.0)

    def record_strategy_run(self, run_id: str, strategy_name: str, symbol: str, completed_at: str, metrics: dict[str, float]) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("INSERT OR REPLACE INTO strategy_runs VALUES (?, ?, ?, ?, ?)", (run_id, strategy_name, symbol, completed_at, json.dumps(metrics)))

    def strategy_leaderboard(self) -> pd.DataFrame:
        with closing(self._connect()) as connection:
            frame = pd.read_sql_query("SELECT strategy_name, metrics_json FROM strategy_runs", connection)
        if frame.empty: return pd.DataFrame(columns=["strategy_name", "runs", "average_total_return", "average_sharpe"])
        metrics = frame["metrics_json"].map(json.loads)
        frame["total_return"] = metrics.map(lambda x: x.get("total_return", 0.0))
        frame["sharpe"] = metrics.map(lambda x: x.get("sharpe_ratio", 0.0))
        return frame.groupby("strategy_name", as_index=False).agg(runs=("strategy_name", "size"), average_total_return=("total_return", "mean"), average_sharpe=("sharpe", "mean")).sort_values(["average_sharpe", "average_total_return"], ascending=False, ignore_index=True)

    def strategy_history(self, limit: int = 100) -> pd.DataFrame:
        with closing(self._connect()) as connection:
            frame = pd.read_sql_query("SELECT strategy_name, symbol, completed_at, metrics_json FROM strategy_runs ORDER BY completed_at DESC LIMIT ?", connection, params=[limit])
        if frame.empty: return frame
        metrics = pd.DataFrame.from_records(frame.pop("metrics_json").map(json.loads).tolist(), index=frame.index)
        return pd.concat([frame, metrics], axis=1)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    @staticmethod
    def _validate_bars(bars: pd.DataFrame) -> None:
        missing = set(REQUIRED_COLUMNS) - set(bars.columns)
        if missing:
            raise ValueError(f"Missing required OHLCV columns: {sorted(missing)}")
        if not isinstance(bars.index, pd.DatetimeIndex):
            raise ValueError("Bars must use a DatetimeIndex")
        if bars.index.has_duplicates:
            raise ValueError("Bars must not contain duplicate timestamps")
