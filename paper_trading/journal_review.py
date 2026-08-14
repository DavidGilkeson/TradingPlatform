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
    execution_rating INTEGER,
    next_time_action TEXT,
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
            columns={row["name"] for row in c.execute(
                "PRAGMA table_info(paper_trade_reviews)").fetchall()}
            if "execution_rating" not in columns:
                c.execute(
                    "ALTER TABLE paper_trade_reviews ADD COLUMN execution_rating INTEGER")
            if "next_time_action" not in columns:
                c.execute(
                    "ALTER TABLE paper_trade_reviews ADD COLUMN next_time_action TEXT")

    def save_review(self, *, account_id, trade_id, followed_plan,
                    what_worked, what_went_wrong, lesson_learned,
                    emotional_state, execution_rating=None,
                    next_time_action=""):
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as c:
            c.execute("""
                INSERT INTO paper_trade_reviews(
                    account_id,trade_id,followed_plan,what_worked,
                    what_went_wrong,lesson_learned,emotional_state,
                    execution_rating,next_time_action,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(trade_id) DO UPDATE SET
                    followed_plan=excluded.followed_plan,
                    what_worked=excluded.what_worked,
                    what_went_wrong=excluded.what_went_wrong,
                    lesson_learned=excluded.lesson_learned,
                    emotional_state=excluded.emotional_state,
                    execution_rating=excluded.execution_rating,
                    next_time_action=excluded.next_time_action,
                    updated_at=excluded.updated_at
            """, (
                account_id, trade_id,
                None if followed_plan is None else int(followed_plan),
                what_worked.strip(), what_went_wrong.strip(),
                lesson_learned.strip(), emotional_state.strip(),
                execution_rating, next_time_action.strip(), now, now
            ))

    def get_review(self, trade_id):
        with self.database.connect() as c:
            row = c.execute(
                "SELECT * FROM paper_trade_reviews WHERE trade_id=?",
                (trade_id,)
            ).fetchone()
        return dict(row) if row else None
