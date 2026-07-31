from __future__ import annotations
from datetime import datetime, timezone
from .database import PaperTradingDatabase
from .models import PaperAccount, PaperPosition

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)

class PaperTradingRepository:
    def __init__(self, database: PaperTradingDatabase) -> None:
        self.database = database

    def create_account(self, name="Atlas Paper Account", starting_balance=100000.0):
        if not name.strip():
            raise ValueError("Account name cannot be empty.")
        if starting_balance <= 0:
            raise ValueError("Starting balance must be greater than zero.")
        now = utc_now()
        with self.database.connect() as c:
            c.execute("UPDATE paper_accounts SET is_active=0, updated_at=?", (now,))
            cur = c.execute(
                "INSERT INTO paper_accounts(name,starting_balance,cash,is_active,created_at,updated_at) VALUES(?,?,?,1,?,?)",
                (name.strip(), starting_balance, starting_balance, now, now),
            )
            account_id = cur.lastrowid
        return self.get_account(account_id)

    def get_account(self, account_id: int):
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise LookupError("Account not found.")
        return self._account(row)

    def get_active_account(self):
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM paper_accounts WHERE is_active=1 ORDER BY id DESC LIMIT 1").fetchone()
        return self._account(row) if row else None

    def ensure_active_account(self, name="Atlas Paper Account", starting_balance=100000.0):
        return self.get_active_account() or self.create_account(name, starting_balance)

    def update_cash(self, account_id: int, cash: float):
        if cash < 0:
            raise ValueError("Cash cannot be negative.")
        with self.database.connect() as c:
            c.execute("UPDATE paper_accounts SET cash=?, updated_at=? WHERE id=?", (cash, utc_now(), account_id))
        return self.get_account(account_id)

    def list_positions(self, account_id: int):
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM paper_positions WHERE account_id=? ORDER BY ticker", (account_id,)).fetchall()
        return [self._position(r) for r in rows]

    def upsert_position(self, account_id, ticker, shares, average_entry_price, current_price=None):
        ticker = ticker.upper().strip()
        current_price = current_price or average_entry_price
        if not ticker or shares <= 0 or average_entry_price <= 0 or current_price <= 0:
            raise ValueError("Invalid position values.")
        now = utc_now()
        with self.database.connect() as c:
            c.execute("""
                INSERT INTO paper_positions(account_id,ticker,shares,average_entry_price,current_price,opened_at,updated_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(account_id,ticker) DO UPDATE SET
                shares=excluded.shares, average_entry_price=excluded.average_entry_price,
                current_price=excluded.current_price, updated_at=excluded.updated_at
            """, (account_id,ticker,shares,average_entry_price,current_price,now,now))
            row = c.execute("SELECT * FROM paper_positions WHERE account_id=? AND ticker=?", (account_id,ticker)).fetchone()
        return self._position(row)

    def update_position_prices(self, account_id, prices):
        now = utc_now()
        with self.database.connect() as c:
            for ticker, price in prices.items():
                if float(price) > 0:
                    c.execute("UPDATE paper_positions SET current_price=?,updated_at=? WHERE account_id=? AND ticker=?",
                              (float(price), now, account_id, ticker.upper().strip()))

    def realised_pnl(self, account_id):
        with self.database.connect() as c:
            row = c.execute("SELECT COALESCE(SUM(realised_pnl),0) AS pnl FROM paper_trades WHERE account_id=?", (account_id,)).fetchone()
        return float(row["pnl"])

    def record_snapshot(self, account_id, cash, positions_value, equity, unrealised_pnl, realised_pnl):
        with self.database.connect() as c:
            c.execute("""INSERT INTO paper_account_snapshots
                (account_id,cash,positions_value,equity,unrealised_pnl,realised_pnl,captured_at)
                VALUES(?,?,?,?,?,?,?)""",
                (account_id,cash,positions_value,equity,unrealised_pnl,realised_pnl,utc_now()))

    def list_snapshots(self, account_id):
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM paper_account_snapshots WHERE account_id=? ORDER BY captured_at",(account_id,)).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _account(r):
        return PaperAccount(int(r["id"]), str(r["name"]), float(r["starting_balance"]), float(r["cash"]),
                            parse_datetime(r["created_at"]), parse_datetime(r["updated_at"]), bool(r["is_active"]))

    @staticmethod
    def _position(r):
        return PaperPosition(int(r["id"]), int(r["account_id"]), str(r["ticker"]), float(r["shares"]),
                             float(r["average_entry_price"]), float(r["current_price"]),
                             parse_datetime(r["opened_at"]), parse_datetime(r["updated_at"]))
