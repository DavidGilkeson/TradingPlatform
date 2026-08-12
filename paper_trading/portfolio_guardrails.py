"""Portfolio-wide safety guardrails for Atlas paper trading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from .journal_analytics import build_trade_journal_frame
from .portfolio_analytics import build_positions_frame


@dataclass(slots=True)
class GuardrailSettings:
    max_total_exposure_pct: float = 80.0
    max_open_positions: int = 8
    daily_loss_limit_pct: float = 3.0
    consecutive_loss_limit: int = 3


@dataclass(slots=True)
class GuardrailStatus:
    trading_allowed: bool
    exposure_pct: float
    open_positions: int
    daily_realised_pnl: float
    daily_loss_pct: float
    consecutive_losses: int
    blockers: list[str]
    warnings: list[str]


def _current_loss_streak(trades: pd.DataFrame) -> int:
    if trades is None or trades.empty or "realised_pnl" not in trades.columns:
        return 0

    ordered = trades.copy()

    if "exit_date" in ordered.columns:
        ordered["exit_date"] = pd.to_datetime(
            ordered["exit_date"],
            errors="coerce",
            utc=True,
        )
        ordered = ordered.sort_values("exit_date")

    pnl = pd.to_numeric(
        ordered["realised_pnl"],
        errors="coerce",
    ).fillna(0.0)

    streak = 0
    for value in reversed(pnl.tolist()):
        if value < 0:
            streak += 1
        else:
            break

    return streak


def _daily_realised_pnl(
    trades: pd.DataFrame,
    *,
    trading_date: date | None = None,
) -> float:
    if trades is None or trades.empty:
        return 0.0
    if "exit_date" not in trades.columns or "realised_pnl" not in trades.columns:
        return 0.0

    trading_date = trading_date or date.today()

    frame = trades.copy()
    frame["exit_date"] = pd.to_datetime(
        frame["exit_date"],
        errors="coerce",
        utc=True,
    )
    frame["realised_pnl"] = pd.to_numeric(
        frame["realised_pnl"],
        errors="coerce",
    ).fillna(0.0)

    mask = frame["exit_date"].dt.date == trading_date
    return float(frame.loc[mask, "realised_pnl"].sum())


def evaluate_portfolio_guardrails(
    service,
    *,
    settings: GuardrailSettings | None = None,
    trading_date: date | None = None,
) -> GuardrailStatus:
    """Evaluate whether Atlas should permit new paper BUY entries."""

    settings = settings or GuardrailSettings()
    snapshot = service.snapshot(persist=False)

    positions = build_positions_frame(service)
    trades = build_trade_journal_frame(service)

    if positions is None or positions.empty:
        open_positions = 0
        total_position_value = 0.0
    else:
        open_positions = len(positions)
        value_column = next(
            (
                column
                for column in (
                    "Market Value",
                    "market_value",
                    "Position Value",
                    "position_value",
                )
                if column in positions.columns
            ),
            None,
        )
        total_position_value = (
            float(
                pd.to_numeric(
                    positions[value_column],
                    errors="coerce",
                ).fillna(0.0).sum()
            )
            if value_column
            else 0.0
        )

    equity = float(snapshot.equity)
    exposure_pct = (
        total_position_value / equity * 100.0
        if equity > 0
        else 0.0
    )

    daily_pnl = _daily_realised_pnl(
        trades,
        trading_date=trading_date,
    )

    daily_loss_pct = (
        abs(min(daily_pnl, 0.0)) / equity * 100.0
        if equity > 0
        else 0.0
    )

    loss_streak = _current_loss_streak(trades)

    blockers: list[str] = []
    warnings: list[str] = []

    if exposure_pct >= settings.max_total_exposure_pct:
        blockers.append(
            f"Portfolio exposure is {exposure_pct:.1f}%, at or above "
            f"the {settings.max_total_exposure_pct:.1f}% limit."
        )

    if open_positions >= settings.max_open_positions:
        blockers.append(
            f"{open_positions} positions are already open; "
            f"the limit is {settings.max_open_positions}."
        )

    if daily_loss_pct >= settings.daily_loss_limit_pct:
        blockers.append(
            f"Today's realised loss is {daily_loss_pct:.2f}% of equity, "
            f"at or above the {settings.daily_loss_limit_pct:.2f}% daily limit."
        )

    if loss_streak >= settings.consecutive_loss_limit:
        blockers.append(
            f"{loss_streak} consecutive losing trades reached the "
            f"{settings.consecutive_loss_limit}-loss pause limit."
        )

    if (
        exposure_pct >= settings.max_total_exposure_pct * 0.8
        and exposure_pct < settings.max_total_exposure_pct
    ):
        warnings.append("Portfolio exposure is approaching its maximum limit.")

    if (
        open_positions >= max(settings.max_open_positions - 1, 1)
        and open_positions < settings.max_open_positions
    ):
        warnings.append("You are one position away from the open-position limit.")

    return GuardrailStatus(
        trading_allowed=not blockers,
        exposure_pct=exposure_pct,
        open_positions=open_positions,
        daily_realised_pnl=daily_pnl,
        daily_loss_pct=daily_loss_pct,
        consecutive_losses=loss_streak,
        blockers=blockers,
        warnings=warnings,
    )


def validate_new_position_against_exposure(
    *,
    account_equity: float,
    current_exposure_value: float,
    proposed_position_value: float,
    max_total_exposure_pct: float,
) -> tuple[bool, float]:
    """Check projected exposure after adding a proposed position."""

    if account_equity <= 0:
        return False, 0.0

    projected_value = current_exposure_value + proposed_position_value
    projected_pct = projected_value / account_equity * 100.0

    return projected_pct <= max_total_exposure_pct, projected_pct
