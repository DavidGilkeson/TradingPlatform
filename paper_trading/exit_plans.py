"""Stop-loss and take-profit planning for Atlas paper positions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .database import PaperTradingDatabase


EXIT_PLAN_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_exit_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    stop_price REAL,
    target_price REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, ticker),
    FOREIGN KEY(account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE
);
"""


@dataclass(slots=True)
class ExitPlan:
    account_id: int
    ticker: str
    stop_price: float | None
    target_price: float | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class ExitPlanStatus:
    ticker: str
    current_price: float
    stop_price: float | None
    target_price: float | None
    distance_to_stop_pct: float | None
    distance_to_target_pct: float | None
    stop_triggered: bool
    target_triggered: bool
    reward_risk_ratio: float | None


class ExitPlanRepository:
    """Persist and retrieve stop/target plans."""

    def __init__(self, db_path: str = "data/paper_trading.db") -> None:
        self.database = PaperTradingDatabase(db_path)
        self._initialise()

    def _initialise(self) -> None:
        with self.database.connect() as connection:
            connection.executescript(EXIT_PLAN_SCHEMA)

    def save_plan(
        self,
        *,
        account_id: int,
        ticker: str,
        stop_price: float | None,
        target_price: float | None,
    ) -> ExitPlan:
        ticker = ticker.upper().strip()
        if not ticker:
            raise ValueError("Ticker cannot be empty.")

        if stop_price is not None and stop_price <= 0:
            raise ValueError("Stop price must be greater than zero.")

        if target_price is not None and target_price <= 0:
            raise ValueError("Target price must be greater than zero.")

        now = datetime.now(timezone.utc).isoformat()

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO paper_exit_plans (
                    account_id,
                    ticker,
                    stop_price,
                    target_price,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, ticker)
                DO UPDATE SET
                    stop_price = excluded.stop_price,
                    target_price = excluded.target_price,
                    updated_at = excluded.updated_at
                """,
                (
                    account_id,
                    ticker,
                    stop_price,
                    target_price,
                    now,
                    now,
                ),
            )

        plan = self.get_plan(account_id=account_id, ticker=ticker)
        if plan is None:
            raise RuntimeError("Exit plan was not saved.")
        return plan

    def get_plan(
        self,
        *,
        account_id: int,
        ticker: str,
    ) -> ExitPlan | None:
        ticker = ticker.upper().strip()

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM paper_exit_plans
                WHERE account_id = ? AND ticker = ?
                """,
                (account_id, ticker),
            ).fetchone()

        if row is None:
            return None

        return ExitPlan(
            account_id=int(row["account_id"]),
            ticker=str(row["ticker"]),
            stop_price=(
                float(row["stop_price"])
                if row["stop_price"] is not None
                else None
            ),
            target_price=(
                float(row["target_price"])
                if row["target_price"] is not None
                else None
            ),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def delete_plan(
        self,
        *,
        account_id: int,
        ticker: str,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                DELETE FROM paper_exit_plans
                WHERE account_id = ? AND ticker = ?
                """,
                (account_id, ticker.upper().strip()),
            )

    def list_plans(self, account_id: int) -> list[ExitPlan]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM paper_exit_plans
                WHERE account_id = ?
                ORDER BY ticker
                """,
                (account_id,),
            ).fetchall()

        return [
            ExitPlan(
                account_id=int(row["account_id"]),
                ticker=str(row["ticker"]),
                stop_price=(
                    float(row["stop_price"])
                    if row["stop_price"] is not None
                    else None
                ),
                target_price=(
                    float(row["target_price"])
                    if row["target_price"] is not None
                    else None
                ),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]


def validate_exit_plan(
    *,
    entry_price: float,
    stop_price: float | None,
    target_price: float | None,
) -> None:
    """Validate a long-position stop/target plan."""

    if entry_price <= 0:
        raise ValueError("Entry price must be greater than zero.")

    if stop_price is not None and stop_price >= entry_price:
        raise ValueError(
            "For a long position, stop price must be below entry price."
        )

    if target_price is not None and target_price <= entry_price:
        raise ValueError(
            "For a long position, target price must be above entry price."
        )


def evaluate_exit_plan(
    *,
    ticker: str,
    entry_price: float,
    current_price: float,
    stop_price: float | None,
    target_price: float | None,
) -> ExitPlanStatus:
    """Calculate current distance to planned stop and target."""

    if entry_price <= 0 or current_price <= 0:
        raise ValueError("Entry and current prices must be greater than zero.")

    validate_exit_plan(
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
    )

    distance_to_stop_pct = None
    stop_triggered = False

    if stop_price is not None:
        distance_to_stop_pct = (
            current_price - stop_price
        ) / current_price
        stop_triggered = current_price <= stop_price

    distance_to_target_pct = None
    target_triggered = False

    if target_price is not None:
        distance_to_target_pct = (
            target_price - current_price
        ) / current_price
        target_triggered = current_price >= target_price

    reward_risk_ratio = None

    if stop_price is not None and target_price is not None:
        risk = entry_price - stop_price
        reward = target_price - entry_price
        if risk > 0:
            reward_risk_ratio = reward / risk

    return ExitPlanStatus(
        ticker=ticker.upper().strip(),
        current_price=current_price,
        stop_price=stop_price,
        target_price=target_price,
        distance_to_stop_pct=distance_to_stop_pct,
        distance_to_target_pct=distance_to_target_pct,
        stop_triggered=stop_triggered,
        target_triggered=target_triggered,
        reward_risk_ratio=reward_risk_ratio,
    )
