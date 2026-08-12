from dataclasses import dataclass
from datetime import datetime, timezone
from .database import PaperTradingDatabase

SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_exit_audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL,
 ticker TEXT NOT NULL, decision TEXT NOT NULL, current_price REAL NOT NULL,
 stop_price REAL, target_price REAL, details TEXT, created_at TEXT NOT NULL
);
"""

@dataclass(slots=True)
class ExitAuditRecord:
    id:int; account_id:int; ticker:str; decision:str; current_price:float
    stop_price:float|None; target_price:float|None; details:str; created_at:str

class ExitAuditRepository:
    def __init__(self, db_path="data/paper_trading.db"):
        self.database=PaperTradingDatabase(db_path)
        with self.database.connect() as c: c.executescript(SCHEMA)

    def record(self, *, account_id, ticker, decision, current_price,
               stop_price=None, target_price=None, details=""):
        now=datetime.now(timezone.utc).isoformat()
        with self.database.connect() as c:
            cur=c.execute("""INSERT INTO paper_exit_audit
            (account_id,ticker,decision,current_price,stop_price,target_price,details,created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (account_id,ticker.upper().strip(),decision,float(current_price),
             stop_price,target_price,details,now))
            return int(cur.lastrowid)

    def list_records(self, *, account_id, limit=200):
        with self.database.connect() as c:
            rows=c.execute("""SELECT * FROM paper_exit_audit WHERE account_id=?
            ORDER BY id DESC LIMIT ?""",(account_id,int(limit))).fetchall()
        return [ExitAuditRecord(
            int(r["id"]),int(r["account_id"]),str(r["ticker"]),str(r["decision"]),
            float(r["current_price"]),
            float(r["stop_price"]) if r["stop_price"] is not None else None,
            float(r["target_price"]) if r["target_price"] is not None else None,
            str(r["details"] or ""),str(r["created_at"])) for r in rows]
