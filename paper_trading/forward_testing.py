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

CREATE TABLE IF NOT EXISTS paper_forward_test_outcomes (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 forward_test_id INTEGER NOT NULL,
 horizon_days INTEGER NOT NULL,
 observed_price REAL NOT NULL CHECK(observed_price > 0),
 observed_at TEXT NOT NULL,
 return_pct REAL,
 UNIQUE(forward_test_id, horizon_days),
 FOREIGN KEY(forward_test_id) REFERENCES paper_forward_tests(id) ON DELETE CASCADE
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


class ForwardTestOutcomeRepository:
    def __init__(self, db_path="data/paper_trading.db"):
        self.database = PaperTradingDatabase(db_path)
        with self.database.connect() as c:
            c.executescript(SCHEMA)

    def save_outcome(
        self,
        *,
        forward_test_id,
        horizon_days,
        observed_price,
        observed_at=None,
    ):
        if int(horizon_days) <= 0:
            raise ValueError("horizon_days must be greater than zero")
        if float(observed_price) <= 0:
            raise ValueError("observed_price must be greater than zero")

        observed_at = observed_at or datetime.now(timezone.utc).isoformat()

        with self.database.connect() as c:
            row = c.execute(
                "SELECT market_price FROM paper_forward_tests WHERE id=?",
                (int(forward_test_id),),
            ).fetchone()

            if row is None:
                raise ValueError("forward-test decision does not exist")

            entry_price = row["market_price"]
            return_pct = None

            if entry_price is not None and float(entry_price) > 0:
                return_pct = (
                    (float(observed_price) - float(entry_price))
                    / float(entry_price)
                ) * 100.0

            c.execute(
                """INSERT INTO paper_forward_test_outcomes
                (forward_test_id,horizon_days,observed_price,observed_at,return_pct)
                VALUES (?,?,?,?,?)
                ON CONFLICT(forward_test_id,horizon_days) DO UPDATE SET
                 observed_price=excluded.observed_price,
                 observed_at=excluded.observed_at,
                 return_pct=excluded.return_pct""",
                (
                    int(forward_test_id),
                    int(horizon_days),
                    float(observed_price),
                    observed_at,
                    return_pct,
                ),
            )

    def outcomes(self, account_id):
        with self.database.connect() as c:
            return pd.read_sql_query(
                """SELECT
                    f.id AS forward_test_id,
                    f.ticker,
                    f.decision,
                    f.atlas_score,
                    f.confidence,
                    f.market_price AS entry_price,
                    f.signal,
                    f.reason,
                    f.recorded_at,
                    o.horizon_days,
                    o.observed_price,
                    o.observed_at,
                    o.return_pct
                FROM paper_forward_tests f
                JOIN paper_forward_test_outcomes o
                  ON o.forward_test_id=f.id
                WHERE f.account_id=?
                ORDER BY o.observed_at DESC,f.id DESC""",
                c,
                params=(int(account_id),),
            )


def outcome_comparison(frame):
    """Compare TAKEN and SKIPPED opportunities at each observation horizon."""
    if frame is None or frame.empty:
        return pd.DataFrame()

    working = frame.copy()
    working["return_pct"] = pd.to_numeric(
        working["return_pct"], errors="coerce"
    )
    working = working.dropna(subset=["return_pct"])

    if working.empty:
        return pd.DataFrame()

    rows = []

    for (horizon, decision), group in working.groupby(
        ["horizon_days", "decision"]
    ):
        rows.append(
            {
                "Horizon Days": int(horizon),
                "Decision": str(decision),
                "Observations": int(len(group)),
                "Positive Rate": float((group["return_pct"] > 0).mean()),
                "Average Return": float(group["return_pct"].mean()),
                "Median Return": float(group["return_pct"].median()),
                "Best Return": float(group["return_pct"].max()),
                "Worst Return": float(group["return_pct"].min()),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["Horizon Days", "Decision"]
    ).reset_index(drop=True)


def decision_quality(frame, horizon_days):
    """Summarise whether TAKEN opportunities outperformed SKIPPED ones."""
    if frame is None or frame.empty:
        return None

    subset = frame[
        pd.to_numeric(frame["horizon_days"], errors="coerce")
        == int(horizon_days)
    ].copy()

    subset["return_pct"] = pd.to_numeric(
        subset["return_pct"], errors="coerce"
    )
    subset = subset.dropna(subset=["return_pct"])

    taken = subset[subset["decision"].astype(str).str.upper() == "TAKEN"]
    skipped = subset[subset["decision"].astype(str).str.upper() == "SKIPPED"]

    if taken.empty or skipped.empty:
        return None

    taken_return = float(taken["return_pct"].mean())
    skipped_return = float(skipped["return_pct"].mean())

    return {
        "horizon_days": int(horizon_days),
        "taken_average_return": taken_return,
        "skipped_average_return": skipped_return,
        "decision_edge": taken_return - skipped_return,
        "taken_count": len(taken),
        "skipped_count": len(skipped),
    }
