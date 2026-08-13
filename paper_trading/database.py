from __future__ import annotations
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS paper_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    starting_balance REAL NOT NULL CHECK(starting_balance > 0),
    cash REAL NOT NULL CHECK(cash >= 0),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    shares REAL NOT NULL CHECK(shares > 0),
    average_entry_price REAL NOT NULL CHECK(average_entry_price > 0),
    current_price REAL NOT NULL CHECK(current_price > 0),
    opened_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, ticker),
    FOREIGN KEY(account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS paper_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
    order_type TEXT NOT NULL DEFAULT 'MARKET',
    requested_shares REAL NOT NULL CHECK(requested_shares > 0),
    requested_price REAL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    filled_at TEXT,
    filled_price REAL,
    commission REAL NOT NULL DEFAULT 0,
    slippage REAL NOT NULL DEFAULT 0,
    notes TEXT,
    FOREIGN KEY(account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    exit_date TEXT NOT NULL,
    shares REAL NOT NULL CHECK(shares > 0),
    entry_price REAL NOT NULL CHECK(entry_price > 0),
    exit_price REAL NOT NULL CHECK(exit_price > 0),
    realised_pnl REAL NOT NULL,
    return_pct REAL NOT NULL,
    commission REAL NOT NULL DEFAULT 0,
    FOREIGN KEY(account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS paper_position_lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    buy_order_id INTEGER NOT NULL,
    shares_original REAL NOT NULL CHECK(shares_original > 0),
    shares_remaining REAL NOT NULL CHECK(shares_remaining >= 0),
    entry_price REAL NOT NULL CHECK(entry_price > 0),
    opened_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE,
    FOREIGN KEY(buy_order_id) REFERENCES paper_orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS paper_trade_entry_links (
    trade_id INTEGER NOT NULL,
    buy_order_id INTEGER NOT NULL,
    allocated_shares REAL NOT NULL CHECK(allocated_shares > 0),
    allocation_weight REAL NOT NULL CHECK(allocation_weight > 0 AND allocation_weight <= 1),
    PRIMARY KEY(trade_id, buy_order_id),
    FOREIGN KEY(trade_id) REFERENCES paper_trades(id) ON DELETE CASCADE,
    FOREIGN KEY(buy_order_id) REFERENCES paper_orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS paper_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    order_id INTEGER,
    ticker TEXT,
    action TEXT,
    reason TEXT,
    notes TEXT,
    confidence INTEGER CHECK(confidence BETWEEN 1 AND 10),
    atlas_score REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE,
    FOREIGN KEY(order_id) REFERENCES paper_orders(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS paper_account_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    cash REAL NOT NULL,
    positions_value REAL NOT NULL,
    equity REAL NOT NULL,
    unrealised_pnl REAL NOT NULL,
    realised_pnl REAL NOT NULL,
    captured_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE
);
"""

class PaperTradingDatabase:
    def __init__(self, db_path: str | Path = "data/paper_trading.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialise()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialise(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def reset_all(self) -> None:
        with self.connect() as connection:
            for table in [
                "paper_account_snapshots",
                "paper_trade_entry_links",
                "paper_position_lots",
                "paper_journal",
                "paper_trades",
                "paper_orders",
                "paper_positions",
                "paper_accounts",
            ]:
                connection.execute(f"DELETE FROM {table}")
            connection.execute("DELETE FROM sqlite_sequence WHERE name LIKE 'paper_%'")
