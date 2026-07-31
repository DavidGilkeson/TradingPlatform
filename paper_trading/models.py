from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(slots=True)
class PaperAccount:
    id: int
    name: str
    starting_balance: float
    cash: float
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    @property
    def buying_power(self) -> float:
        return self.cash

@dataclass(slots=True)
class PaperPosition:
    id: int
    account_id: int
    ticker: str
    shares: float
    average_entry_price: float
    current_price: float
    opened_at: datetime
    updated_at: datetime

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.shares * self.average_entry_price

    @property
    def unrealised_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealised_return_pct(self) -> float:
        return self.unrealised_pnl / self.cost_basis if self.cost_basis else 0.0

@dataclass(slots=True)
class AccountSnapshot:
    account_id: int
    cash: float
    positions_value: float
    equity: float
    unrealised_pnl: float
    realised_pnl: float
    total_return_pct: float
    open_positions: int
