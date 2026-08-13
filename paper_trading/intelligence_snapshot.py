"""Persistent entry-time intelligence snapshots for paper BUY orders."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from .database import PaperTradingDatabase

SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_intelligence_snapshots (
    order_id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    atlas_score REAL,
    confidence REAL,
    trend_regime TEXT,
    volatility_regime TEXT,
    historical_match_score INTEGER,
    matched_trades INTEGER,
    historical_win_rate REAL,
    historical_expectancy REAL,
    evidence_level TEXT,
    sample_grade TEXT,
    reliability INTEGER,
    historical_verdict TEXT,
    created_at TEXT NOT NULL
);
"""

@dataclass(slots=True)
class IntelligenceSnapshot:
    order_id:int
    account_id:int
    ticker:str
    atlas_score:float|None
    confidence:float|None
    trend_regime:str|None
    volatility_regime:str|None
    historical_match_score:int
    matched_trades:int
    historical_win_rate:float|None
    historical_expectancy:float|None
    evidence_level:str
    sample_grade:str
    reliability:int
    historical_verdict:str
    created_at:str

class IntelligenceSnapshotRepository:
    def __init__(self, db_path="data/paper_trading.db"):
        self.database=PaperTradingDatabase(db_path)
        with self.database.connect() as c:
            c.executescript(SCHEMA)

    def save(self, *, order_id, account_id, ticker, atlas_score=None,
             confidence=None, trend_regime=None, volatility_regime=None,
             historical_match_score=0, matched_trades=0,
             historical_win_rate=None, historical_expectancy=None,
             evidence_level="", sample_grade="", reliability=0,
             historical_verdict=""):
        now=datetime.now(timezone.utc).isoformat()
        with self.database.connect() as c:
            c.execute("""INSERT INTO paper_intelligence_snapshots
            (order_id,account_id,ticker,atlas_score,confidence,trend_regime,
             volatility_regime,historical_match_score,matched_trades,
             historical_win_rate,historical_expectancy,evidence_level,
             sample_grade,reliability,historical_verdict,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(order_id) DO UPDATE SET
             atlas_score=excluded.atlas_score,
             confidence=excluded.confidence,
             trend_regime=excluded.trend_regime,
             volatility_regime=excluded.volatility_regime,
             historical_match_score=excluded.historical_match_score,
             matched_trades=excluded.matched_trades,
             historical_win_rate=excluded.historical_win_rate,
             historical_expectancy=excluded.historical_expectancy,
             evidence_level=excluded.evidence_level,
             sample_grade=excluded.sample_grade,
             reliability=excluded.reliability,
             historical_verdict=excluded.historical_verdict""",
            (int(order_id),int(account_id),ticker.upper().strip(),atlas_score,
             confidence,trend_regime,volatility_regime,
             int(historical_match_score),int(matched_trades),
             historical_win_rate,historical_expectancy,evidence_level,
             sample_grade,int(reliability),historical_verdict,now))

    def get(self, order_id):
        with self.database.connect() as c:
            r=c.execute("SELECT * FROM paper_intelligence_snapshots WHERE order_id=?",
                        (int(order_id),)).fetchone()
        if r is None: return None
        return IntelligenceSnapshot(
            int(r["order_id"]),int(r["account_id"]),str(r["ticker"]),
            float(r["atlas_score"]) if r["atlas_score"] is not None else None,
            float(r["confidence"]) if r["confidence"] is not None else None,
            str(r["trend_regime"]) if r["trend_regime"] is not None else None,
            str(r["volatility_regime"]) if r["volatility_regime"] is not None else None,
            int(r["historical_match_score"]),int(r["matched_trades"]),
            float(r["historical_win_rate"]) if r["historical_win_rate"] is not None else None,
            float(r["historical_expectancy"]) if r["historical_expectancy"] is not None else None,
            str(r["evidence_level"] or ""),str(r["sample_grade"] or ""),
            int(r["reliability"]),str(r["historical_verdict"] or ""),
            str(r["created_at"]))
