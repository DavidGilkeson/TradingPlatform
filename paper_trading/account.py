from .database import PaperTradingDatabase
from .models import AccountSnapshot
from .repository import PaperTradingRepository

class PaperAccountService:
    def __init__(self, db_path="data/paper_trading.db"):
        self.database = PaperTradingDatabase(db_path)
        self.repository = PaperTradingRepository(self.database)

    def initialise_account(self, name="Atlas Paper Account", starting_balance=100000.0):
        return self.repository.ensure_active_account(name, starting_balance)

    def active_account(self):
        return self.repository.get_active_account() or self.initialise_account()

    def reset_account(self, name="Atlas Paper Account", starting_balance=100000.0):
        self.database.reset_all()
        return self.repository.create_account(name, starting_balance)

    def update_market_prices(self, prices):
        account = self.active_account()
        self.repository.update_position_prices(account.id, prices)

    def snapshot(self, persist=True):
        account = self.active_account()
        positions = self.repository.list_positions(account.id)
        positions_value = sum(p.market_value for p in positions)
        unrealised_pnl = sum(p.unrealised_pnl for p in positions)
        realised_pnl = self.repository.realised_pnl(account.id)
        equity = account.cash + positions_value
        total_return_pct = equity / account.starting_balance - 1 if account.starting_balance else 0.0
        snap = AccountSnapshot(account.id, account.cash, positions_value, equity,
                               unrealised_pnl, realised_pnl, total_return_pct, len(positions))
        if persist:
            self.repository.record_snapshot(account.id, snap.cash, snap.positions_value, snap.equity,
                                            snap.unrealised_pnl, snap.realised_pnl)
        return snap
