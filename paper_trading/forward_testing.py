"""Prospective forward-test decision tracking."""
from __future__ import annotations
from datetime import datetime, timezone
import pandas as pd
from .database import PaperTradingDatabase

SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_forward_tests (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 account_id INTEGER NOT NULL,
 ticker TEXT NOT NULL,
 decision TEXT NOT NULL,
 atlas_score REAL,
 confidence REAL,
 market_price REAL,
 signal TEXT,
 reason TEXT,
 recorded_at TEXT NOT NULL,
 linked_order_id INTEGER
);
"""

class ForwardTestRepository:
    def __init__(self,db_path="data/paper_trading.db"):
        self.database=PaperTradingDatabase(db_path)
        with self.database.connect() as c: c.executescript(SCHEMA)

    def record(self,*,account_id,ticker,decision,atlas_score=None,
               confidence=None,market_price=None,signal=None,reason=None,
               linked_order_id=None):
        decision=str(decision).upper().strip()
        if decision not in {"TAKEN","SKIPPED","WATCH"}:
            raise ValueError("decision must be TAKEN, SKIPPED or WATCH")
        with self.database.connect() as c:
            cur=c.execute("""INSERT INTO paper_forward_tests
            (account_id,ticker,decision,atlas_score,confidence,market_price,
             signal,reason,recorded_at,linked_order_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (int(account_id),ticker.upper().strip(),decision,atlas_score,
             confidence,market_price,signal,reason,
             datetime.now(timezone.utc).isoformat(),linked_order_id))
            return int(cur.lastrowid)

    def history(self,account_id):
        with self.database.connect() as c:
            return pd.read_sql_query(
                """SELECT id,ticker,decision,atlas_score,confidence,market_price,
                signal,reason,recorded_at,linked_order_id
                FROM paper_forward_tests WHERE account_id=?
                ORDER BY recorded_at DESC,id DESC""",
                c,params=(int(account_id),))

def forward_test_summary(frame):
    if frame is None or frame.empty:
        return {"total":0,"taken":0,"skipped":0,"watch":0,"discipline_rate":None}
    counts=frame["decision"].astype(str).str.upper().value_counts()
    total=len(frame); taken=int(counts.get("TAKEN",0))
    skipped=int(counts.get("SKIPPED",0)); watch=int(counts.get("WATCH",0))
    return {"total":total,"taken":taken,"skipped":skipped,"watch":watch,
            "discipline_rate":(taken+skipped)/total}
