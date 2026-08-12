"""Persistent market-regime metadata for paper trades."""

from __future__ import annotations

from dataclasses import dataclass
from .database import PaperTradingDatabase


SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_trade_regimes (
    trade_id INTEGER PRIMARY KEY,
    market_regime TEXT NOT NULL,
    trend_regime TEXT NOT NULL,
    volatility_regime TEXT NOT NULL
);
"""


@dataclass(slots=True)
class TradeRegimeRecord:
    trade_id: int
    market_regime: str
    trend_regime: str
    volatility_regime: str


class TradeRegimeRepository:
    def __init__(self, db_path: str = "data/paper_trading.db") -> None:
        self.database = PaperTradingDatabase(db_path)
        with self.database.connect() as connection:
            connection.executescript(SCHEMA)

    def save(
        self,
        *,
        trade_id: int,
        market_regime: str,
        trend_regime: str,
        volatility_regime: str,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO paper_trade_regimes
                    (trade_id, market_regime, trend_regime, volatility_regime)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(trade_id) DO UPDATE SET
                    market_regime=excluded.market_regime,
                    trend_regime=excluded.trend_regime,
                    volatility_regime=excluded.volatility_regime
                """,
                (
                    int(trade_id),
                    market_regime,
                    trend_regime,
                    volatility_regime,
                ),
            )

    def get(self, trade_id: int) -> TradeRegimeRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM paper_trade_regimes WHERE trade_id = ?",
                (int(trade_id),),
            ).fetchone()

        if row is None:
            return None

        return TradeRegimeRecord(
            trade_id=int(row["trade_id"]),
            market_regime=str(row["market_regime"]),
            trend_regime=str(row["trend_regime"]),
            volatility_regime=str(row["volatility_regime"]),
        )

    def all_for_trade_ids(self, trade_ids: list[int]) -> dict[int, TradeRegimeRecord]:
        return {
            trade_id: record
            for trade_id in trade_ids
            if (record := self.get(trade_id)) is not None
        }
