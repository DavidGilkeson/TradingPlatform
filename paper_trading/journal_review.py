from __future__ import annotations
from datetime import datetime, timezone
from .database import PaperTradingDatabase

REVIEW_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_trade_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    trade_id INTEGER NOT NULL UNIQUE,
    followed_plan INTEGER,
    what_worked TEXT,
    what_went_wrong TEXT,
    lesson_learned TEXT,
    emotional_state TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE,
    FOREIGN KEY(trade_id) REFERENCES paper_trades(id) ON DELETE CASCADE
);
"""

class PaperTradeReviewRepository:
    def __init__(self, db_path="data/paper_trading.db"):
        self.database = PaperTradingDatabase(db_path)
        with self.database.connect() as c:
            c.executescript(REVIEW_SCHEMA)

    def save_review(self, *, account_id, trade_id, followed_plan,
                    what_worked, what_went_wrong, lesson_learned,
                    emotional_state):
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as c:
            c.execute("""
                INSERT INTO paper_trade_reviews(
                    account_id,trade_id,followed_plan,what_worked,
                    what_went_wrong,lesson_learned,emotional_state,
                    created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(trade_id) DO UPDATE SET
                    followed_plan=excluded.followed_plan,
                    what_worked=excluded.what_worked,
                    what_went_wrong=excluded.what_went_wrong,
                    lesson_learned=excluded.lesson_learned,
                    emotional_state=excluded.emotional_state,
                    updated_at=excluded.updated_at
            """, (
                account_id, trade_id,
                None if followed_plan is None else int(followed_plan),
                what_worked.strip(), what_went_wrong.strip(),
                lesson_learned.strip(), emotional_state.strip(), now, now
            ))

    def get_review(self, trade_id):
        with self.database.connect() as c:
            row = c.execute(
                "SELECT * FROM paper_trade_reviews WHERE trade_id=?",
                (trade_id,)
            ).fetchone()
        return dict(row) if row else None
