"""Validated market-order execution for Atlas paper trading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .database import PaperTradingDatabase
from .repository import PaperTradingRepository


def utc_now() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class OrderExecution:
    """Result returned after a paper order is filled."""

    order_id: int
    account_id: int
    ticker: str
    side: str
    shares: float
    market_price: float
    filled_price: float
    commission: float
    slippage_pct: float
    cash_after: float
    position_shares_after: float
    realised_pnl: float = 0.0


class PaperOrderService:
    """Execute immediate market BUY and SELL orders against SQLite state."""

    def __init__(
        self,
        db_path: str = "data/paper_trading.db",
        *,
        commission: float = 0.0,
        slippage_pct: float = 0.001,
    ) -> None:
        if commission < 0:
            raise ValueError("Commission cannot be negative.")
        if slippage_pct < 0:
            raise ValueError("Slippage cannot be negative.")

        self.database = PaperTradingDatabase(db_path)
        self.repository = PaperTradingRepository(self.database)
        self.commission = float(commission)
        self.slippage_pct = float(slippage_pct)

    def buy_market(
        self,
        *,
        ticker: str,
        shares: float,
        market_price: float,
        reason: str = "",
        notes: str = "",
        confidence: int | None = None,
        atlas_score: float | None = None,
    ) -> OrderExecution:
        """Execute a market BUY order and update cash and position state."""

        ticker = self._normalise_ticker(ticker)
        shares = self._validate_positive(shares, "Shares")
        market_price = self._validate_positive(market_price, "Market price")
        confidence = self._validate_confidence(confidence)

        account = self.repository.ensure_active_account()
        filled_price = market_price * (1 + self.slippage_pct)
        total_cost = (shares * filled_price) + self.commission

        if total_cost > account.cash + 1e-9:
            raise ValueError(
                f"Insufficient buying power. Required ${total_cost:,.2f}, "
                f"available ${account.cash:,.2f}."
            )

        existing = self._get_position(account.id, ticker)
        existing_shares = existing.shares if existing else 0.0
        existing_cost = (
            existing.shares * existing.average_entry_price
            if existing
            else 0.0
        )

        new_shares = existing_shares + shares
        weighted_entry = (
            existing_cost + (shares * filled_price) + self.commission
        ) / new_shares
        cash_after = account.cash - total_cost
        now = utc_now()

        with self.database.connect() as connection:
            order_id = self._insert_order(
                connection=connection,
                account_id=account.id,
                ticker=ticker,
                side="BUY",
                shares=shares,
                market_price=market_price,
                filled_price=filled_price,
                status="FILLED",
                reason=reason,
                notes=notes,
                confidence=confidence,
                atlas_score=atlas_score,
                timestamp=now,
            )

            connection.execute(
                """
                UPDATE paper_accounts
                SET cash = ?, updated_at = ?
                WHERE id = ?
                """,
                (cash_after, now, account.id),
            )

            connection.execute(
                """
                INSERT INTO paper_positions (
                    account_id,
                    ticker,
                    shares,
                    average_entry_price,
                    current_price,
                    opened_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, ticker)
                DO UPDATE SET
                    shares = excluded.shares,
                    average_entry_price = excluded.average_entry_price,
                    current_price = excluded.current_price,
                    updated_at = excluded.updated_at
                """,
                (
                    account.id,
                    ticker,
                    new_shares,
                    weighted_entry,
                    market_price,
                    existing.opened_at.isoformat() if existing else now,
                    now,
                ),
            )

        return OrderExecution(
            order_id=order_id,
            account_id=account.id,
            ticker=ticker,
            side="BUY",
            shares=shares,
            market_price=market_price,
            filled_price=filled_price,
            commission=self.commission,
            slippage_pct=self.slippage_pct,
            cash_after=cash_after,
            position_shares_after=new_shares,
        )

    def sell_market(
        self,
        *,
        ticker: str,
        shares: float,
        market_price: float,
        reason: str = "",
        notes: str = "",
        confidence: int | None = None,
        atlas_score: float | None = None,
    ) -> OrderExecution:
        """Execute a market SELL order and realise P&L."""

        ticker = self._normalise_ticker(ticker)
        shares = self._validate_positive(shares, "Shares")
        market_price = self._validate_positive(market_price, "Market price")
        confidence = self._validate_confidence(confidence)

        account = self.repository.ensure_active_account()
        position = self._get_position(account.id, ticker)

        if position is None:
            raise ValueError(f"No open {ticker} position exists.")

        if shares > position.shares + 1e-9:
            raise ValueError(
                f"Cannot sell {shares:g} shares. "
                f"Only {position.shares:g} shares are held."
            )

        filled_price = market_price * (1 - self.slippage_pct)
        proceeds = (shares * filled_price) - self.commission
        cash_after = account.cash + proceeds
        shares_after = position.shares - shares

        allocated_entry_cost = shares * position.average_entry_price
        realised_pnl = proceeds - allocated_entry_cost
        return_pct = (
            realised_pnl / allocated_entry_cost
            if allocated_entry_cost > 0
            else 0.0
        )
        now = utc_now()

        with self.database.connect() as connection:
            order_id = self._insert_order(
                connection=connection,
                account_id=account.id,
                ticker=ticker,
                side="SELL",
                shares=shares,
                market_price=market_price,
                filled_price=filled_price,
                status="FILLED",
                reason=reason,
                notes=notes,
                confidence=confidence,
                atlas_score=atlas_score,
                timestamp=now,
            )

            connection.execute(
                """
                UPDATE paper_accounts
                SET cash = ?, updated_at = ?
                WHERE id = ?
                """,
                (cash_after, now, account.id),
            )

            if shares_after <= 1e-9:
                connection.execute(
                    """
                    DELETE FROM paper_positions
                    WHERE account_id = ? AND ticker = ?
                    """,
                    (account.id, ticker),
                )
                shares_after = 0.0
            else:
                connection.execute(
                    """
                    UPDATE paper_positions
                    SET shares = ?, current_price = ?, updated_at = ?
                    WHERE account_id = ? AND ticker = ?
                    """,
                    (
                        shares_after,
                        market_price,
                        now,
                        account.id,
                        ticker,
                    ),
                )

            connection.execute(
                """
                INSERT INTO paper_trades (
                    account_id,
                    ticker,
                    entry_date,
                    exit_date,
                    shares,
                    entry_price,
                    exit_price,
                    realised_pnl,
                    return_pct,
                    commission
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account.id,
                    ticker,
                    position.opened_at.isoformat(),
                    now,
                    shares,
                    position.average_entry_price,
                    filled_price,
                    realised_pnl,
                    return_pct,
                    self.commission,
                ),
            )

        return OrderExecution(
            order_id=order_id,
            account_id=account.id,
            ticker=ticker,
            side="SELL",
            shares=shares,
            market_price=market_price,
            filled_price=filled_price,
            commission=self.commission,
            slippage_pct=self.slippage_pct,
            cash_after=cash_after,
            position_shares_after=shares_after,
            realised_pnl=realised_pnl,
        )

    def list_orders(self, account_id: int | None = None) -> list[dict[str, Any]]:
        """Return order history, newest first."""

        account = self.repository.ensure_active_account()
        account_id = account_id or account.id

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM paper_orders
                WHERE account_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (account_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def list_trades(self, account_id: int | None = None) -> list[dict[str, Any]]:
        """Return completed trade records, newest first."""

        account = self.repository.ensure_active_account()
        account_id = account_id or account.id

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM paper_trades
                WHERE account_id = ?
                ORDER BY exit_date DESC, id DESC
                """,
                (account_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def _insert_order(
        self,
        *,
        connection,
        account_id: int,
        ticker: str,
        side: str,
        shares: float,
        market_price: float,
        filled_price: float,
        status: str,
        reason: str,
        notes: str,
        confidence: int | None,
        atlas_score: float | None,
        timestamp: str,
    ) -> int:
        cursor = connection.execute(
            """
            INSERT INTO paper_orders (
                account_id,
                ticker,
                side,
                order_type,
                requested_shares,
                requested_price,
                status,
                created_at,
                filled_at,
                filled_price,
                commission,
                slippage,
                notes
            )
            VALUES (?, ?, ?, 'MARKET', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                ticker,
                side,
                shares,
                market_price,
                status,
                timestamp,
                timestamp,
                filled_price,
                self.commission,
                self.slippage_pct,
                notes,
            ),
        )
        order_id = int(cursor.lastrowid)

        connection.execute(
            """
            INSERT INTO paper_journal (
                account_id,
                order_id,
                ticker,
                action,
                reason,
                notes,
                confidence,
                atlas_score,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                order_id,
                ticker,
                side,
                reason,
                notes,
                confidence,
                atlas_score,
                timestamp,
            ),
        )

        return order_id

    def _get_position(self, account_id: int, ticker: str):
        positions = self.repository.list_positions(account_id)
        return next(
            (position for position in positions if position.ticker == ticker),
            None,
        )

    @staticmethod
    def _normalise_ticker(ticker: str) -> str:
        ticker = str(ticker).upper().strip()
        if not ticker:
            raise ValueError("Ticker cannot be empty.")
        return ticker

    @staticmethod
    def _validate_positive(value: float, label: str) -> float:
        value = float(value)
        if value <= 0:
            raise ValueError(f"{label} must be greater than zero.")
        return value

    @staticmethod
    def _validate_confidence(value: int | None) -> int | None:
        if value is None:
            return None
        value = int(value)
        if not 1 <= value <= 10:
            raise ValueError("Confidence must be between 1 and 10.")
        return value
