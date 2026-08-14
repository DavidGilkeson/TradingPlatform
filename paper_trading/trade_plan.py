"""Structured pre-trade thesis and risk-plan persistence."""

from __future__ import annotations
from datetime import datetime, timezone
from .database import PaperTradingDatabase

PLAN_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_trade_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    buy_order_id INTEGER NOT NULL UNIQUE,
    ticker TEXT NOT NULL,
    thesis TEXT NOT NULL,
    invalidation TEXT,
    entry_price REAL NOT NULL,
    stop_price REAL NOT NULL,
    target_price REAL NOT NULL,
    planned_shares REAL NOT NULL,
    risk_pct REAL,
    max_position_pct REAL,
    minimum_reward_risk REAL,
    planned_reward_risk REAL,
    confidence INTEGER,
    atlas_score REAL,
    market_regime TEXT,
    volatility_regime TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE,
    FOREIGN KEY(buy_order_id) REFERENCES paper_orders(id) ON DELETE CASCADE
);
"""


def reward_risk(entry_price, stop_price, target_price):
    risk=float(entry_price)-float(stop_price)
    reward=float(target_price)-float(entry_price)
    if risk <= 0:
        return None
    return reward/risk


class PaperTradePlanRepository:
    def __init__(self, db_path="data/paper_trading.db"):
        self.database=PaperTradingDatabase(db_path)
        with self.database.connect() as c:
            c.executescript(PLAN_SCHEMA)

    def save(self, *, account_id, buy_order_id, ticker, thesis, invalidation,
             entry_price, stop_price, target_price, planned_shares,
             risk_pct=None, max_position_pct=None, minimum_reward_risk=None,
             confidence=None, atlas_score=None, market_regime=None,
             volatility_regime=None):
        rr=reward_risk(entry_price,stop_price,target_price)
        now=datetime.now(timezone.utc).isoformat()
        with self.database.connect() as c:
            c.execute("""
                INSERT INTO paper_trade_plans(
                    account_id,buy_order_id,ticker,thesis,invalidation,
                    entry_price,stop_price,target_price,planned_shares,
                    risk_pct,max_position_pct,minimum_reward_risk,
                    planned_reward_risk,confidence,atlas_score,
                    market_regime,volatility_regime,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(buy_order_id) DO UPDATE SET
                    thesis=excluded.thesis,
                    invalidation=excluded.invalidation,
                    stop_price=excluded.stop_price,
                    target_price=excluded.target_price,
                    planned_shares=excluded.planned_shares,
                    risk_pct=excluded.risk_pct,
                    max_position_pct=excluded.max_position_pct,
                    minimum_reward_risk=excluded.minimum_reward_risk,
                    planned_reward_risk=excluded.planned_reward_risk,
                    confidence=excluded.confidence,
                    atlas_score=excluded.atlas_score,
                    market_regime=excluded.market_regime,
                    volatility_regime=excluded.volatility_regime
            """,(
                account_id,buy_order_id,str(ticker).upper(),thesis.strip(),
                invalidation.strip(),float(entry_price),float(stop_price),
                float(target_price),float(planned_shares),risk_pct,
                max_position_pct,minimum_reward_risk,rr,confidence,atlas_score,
                market_regime,volatility_regime,now,
            ))

    def get_by_order(self, buy_order_id):
        with self.database.connect() as c:
            row=c.execute(
                "SELECT * FROM paper_trade_plans WHERE buy_order_id=?",
                (buy_order_id,)
            ).fetchone()
        return dict(row) if row else None
