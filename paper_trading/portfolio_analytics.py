from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import pandas as pd
from .account import PaperAccountService

@dataclass(slots=True)
class PortfolioAnalytics:
    cash: float
    invested_value: float
    equity: float
    unrealised_pnl: float
    realised_pnl: float
    total_return_pct: float
    open_positions: int
    winning_positions: int
    losing_positions: int
    largest_winner_ticker: str | None
    largest_winner_return: float
    largest_loser_ticker: str | None
    largest_loser_return: float
    concentration_score: float
    diversification_score: float

def build_positions_frame(service: PaperAccountService) -> pd.DataFrame:
    account = service.active_account()
    positions = service.repository.list_positions(account.id)
    if not positions:
        return pd.DataFrame(columns=["Ticker","Shares","Average Entry","Current Price","Cost Basis","Market Value","Unrealised P&L","Return","Allocation"])
    frame = pd.DataFrame([{
        "Ticker": p.ticker,
        "Shares": p.shares,
        "Average Entry": p.average_entry_price,
        "Current Price": p.current_price,
        "Cost Basis": p.cost_basis,
        "Market Value": p.market_value,
        "Unrealised P&L": p.unrealised_pnl,
        "Return": p.unrealised_return_pct,
    } for p in positions])
    total = float(frame["Market Value"].sum())
    frame["Allocation"] = frame["Market Value"] / total if total > 0 else 0.0
    return frame.sort_values("Market Value", ascending=False).reset_index(drop=True)

def calculate_portfolio_analytics(service: PaperAccountService) -> PortfolioAnalytics:
    snapshot = service.snapshot(persist=False)
    frame = build_positions_frame(service)
    winners = int((frame["Unrealised P&L"] > 0).sum()) if not frame.empty else 0
    losers = int((frame["Unrealised P&L"] < 0).sum()) if not frame.empty else 0
    win_ticker = lose_ticker = None
    win_return = lose_return = 0.0
    if not frame.empty:
        win_row = frame.loc[frame["Return"].idxmax()]
        lose_row = frame.loc[frame["Return"].idxmin()]
        if float(win_row["Return"]) > 0:
            win_ticker, win_return = str(win_row["Ticker"]), float(win_row["Return"])
        if float(lose_row["Return"]) < 0:
            lose_ticker, lose_return = str(lose_row["Ticker"]), float(lose_row["Return"])
    concentration = float((frame["Allocation"] ** 2).sum() * 100) if not frame.empty else 0.0
    diversification = max(0.0, min(100.0, 100.0 - concentration))
    return PortfolioAnalytics(
        snapshot.cash, snapshot.positions_value, snapshot.equity,
        snapshot.unrealised_pnl, snapshot.realised_pnl, snapshot.total_return_pct,
        snapshot.open_positions, winners, losers, win_ticker, win_return,
        lose_ticker, lose_return, concentration, diversification
    )

def get_position_details(service: PaperAccountService, ticker: str) -> dict[str, Any] | None:
    ticker = ticker.upper().strip()
    account = service.active_account()
    position = next((p for p in service.repository.list_positions(account.id) if p.ticker == ticker), None)
    if position is None:
        return None
    with service.database.connect() as c:
        order = c.execute(
            "SELECT * FROM paper_orders WHERE account_id=? AND ticker=? ORDER BY created_at DESC,id DESC LIMIT 1",
            (account.id, ticker),
        ).fetchone()
        journal = c.execute(
            "SELECT * FROM paper_journal WHERE account_id=? AND ticker=? ORDER BY created_at DESC,id DESC LIMIT 1",
            (account.id, ticker),
        ).fetchone()
    return {
        "ticker": position.ticker,
        "shares": position.shares,
        "average_entry_price": position.average_entry_price,
        "current_price": position.current_price,
        "cost_basis": position.cost_basis,
        "market_value": position.market_value,
        "unrealised_pnl": position.unrealised_pnl,
        "unrealised_return_pct": position.unrealised_return_pct,
        "opened_at": position.opened_at,
        "latest_order": dict(order) if order else None,
        "latest_journal": dict(journal) if journal else None,
    }
