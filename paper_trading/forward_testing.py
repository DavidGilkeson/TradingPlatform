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
 market_regime TEXT,
 volatility_regime TEXT,
 trend_strength TEXT,
 regime_benchmark TEXT,
 regime_benchmark_price REAL,
 regime_ma50 REAL,
 regime_ma200 REAL,
 regime_price_vs_ma50_pct REAL,
 regime_price_vs_ma200_pct REAL,
 regime_volatility_pct REAL,
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
 benchmark_ticker TEXT,
 benchmark_entry_price REAL,
 benchmark_observed_price REAL,
 benchmark_return_pct REAL,
 excess_return_pct REAL,
 UNIQUE(forward_test_id, horizon_days),
 FOREIGN KEY(forward_test_id) REFERENCES paper_forward_tests(id) ON DELETE CASCADE
);
"""

class ForwardTestRepository:
    def __init__(self,db_path="data/paper_trading.db"):
        self.database=PaperTradingDatabase(db_path)
        with self.database.connect() as c:
            c.executescript(SCHEMA)
            columns={row["name"] for row in c.execute(
                "PRAGMA table_info(paper_forward_tests)").fetchall()}
            migrations={
                "market_regime":"TEXT",
                "volatility_regime":"TEXT",
                "trend_strength":"TEXT",
                "regime_benchmark":"TEXT",
                "regime_benchmark_price":"REAL",
                "regime_ma50":"REAL",
                "regime_ma200":"REAL",
                "regime_price_vs_ma50_pct":"REAL",
                "regime_price_vs_ma200_pct":"REAL",
                "regime_volatility_pct":"REAL",
            }
            for name,sql_type in migrations.items():
                if name not in columns:
                    c.execute(
                        f"ALTER TABLE paper_forward_tests ADD COLUMN {name} {sql_type}")

    def record(self,*,account_id,ticker,decision,atlas_score=None,
               confidence=None,market_price=None,signal=None,reason=None,
               market_regime=None,volatility_regime=None,trend_strength=None,
               regime_benchmark=None,regime_benchmark_price=None,
               regime_ma50=None,regime_ma200=None,
               regime_price_vs_ma50_pct=None,regime_price_vs_ma200_pct=None,
               regime_volatility_pct=None,linked_order_id=None):
        decision=str(decision).upper().strip()
        if decision not in {"TAKEN","SKIPPED","WATCH"}:
            raise ValueError("decision must be TAKEN, SKIPPED or WATCH")
        with self.database.connect() as c:
            cur=c.execute("""INSERT INTO paper_forward_tests
            (account_id,ticker,decision,atlas_score,confidence,market_price,
             signal,reason,market_regime,volatility_regime,trend_strength,
             regime_benchmark,regime_benchmark_price,regime_ma50,regime_ma200,
             regime_price_vs_ma50_pct,regime_price_vs_ma200_pct,
             regime_volatility_pct,recorded_at,linked_order_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (int(account_id),ticker.upper().strip(),decision,atlas_score,
             confidence,market_price,signal,reason,market_regime,volatility_regime,
             trend_strength,regime_benchmark,regime_benchmark_price,regime_ma50,
             regime_ma200,regime_price_vs_ma50_pct,regime_price_vs_ma200_pct,
             regime_volatility_pct,datetime.now(timezone.utc).isoformat(),
             linked_order_id))
            return int(cur.lastrowid)

    def history(self,account_id):
        with self.database.connect() as c:
            return pd.read_sql_query(
                """SELECT id,ticker,decision,atlas_score,confidence,market_price,
                signal,reason,market_regime,volatility_regime,trend_strength,
                regime_benchmark,regime_benchmark_price,regime_ma50,regime_ma200,
                regime_price_vs_ma50_pct,regime_price_vs_ma200_pct,
                regime_volatility_pct,recorded_at,linked_order_id
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
            columns = {
                row["name"]
                for row in c.execute(
                    "PRAGMA table_info(paper_forward_test_outcomes)"
                ).fetchall()
            }
            migrations = {
                "benchmark_ticker": "TEXT",
                "benchmark_entry_price": "REAL",
                "benchmark_observed_price": "REAL",
                "benchmark_return_pct": "REAL",
                "excess_return_pct": "REAL",
            }
            for name, sql_type in migrations.items():
                if name not in columns:
                    c.execute(
                        f"ALTER TABLE paper_forward_test_outcomes "
                        f"ADD COLUMN {name} {sql_type}"
                    )

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
                    f.market_regime,
                    f.volatility_regime,
                    f.trend_strength,
                    f.regime_benchmark,
                    f.regime_benchmark_price,
                    f.regime_ma50,
                    f.regime_ma200,
                    f.regime_price_vs_ma50_pct,
                    f.regime_price_vs_ma200_pct,
                    f.regime_volatility_pct,
                    f.recorded_at,
                    o.horizon_days,
                    o.observed_price,
                    o.observed_at,
                    o.return_pct,
                    o.benchmark_ticker,
                    o.benchmark_entry_price,
                    o.benchmark_observed_price,
                    o.benchmark_return_pct,
                    o.excess_return_pct
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


STANDARD_FORWARD_HORIZONS = (1, 3, 5, 10, 20)


def due_forward_test_observations(
    decisions,
    outcomes,
    *,
    now=None,
    horizons=STANDARD_FORWARD_HORIZONS,
):
    """Find missing observations whose approximate trading-day horizon is due.

    Business days are used for scheduling. Market-data resolution later chooses
    the first available session on/after the due date, which safely handles
    exchange holidays and weekends.
    """
    if decisions is None or decisions.empty:
        return pd.DataFrame()

    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    else:
        now = now.tz_convert("UTC")

    existing=set()
    if outcomes is not None and not outcomes.empty:
        existing={
            (int(row["forward_test_id"]),int(row["horizon_days"]))
            for _,row in outcomes.iterrows()
        }

    rows=[]
    for _,decision in decisions.iterrows():
        recorded=pd.Timestamp(decision["recorded_at"])
        if recorded.tzinfo is None:
            recorded=recorded.tz_localize("UTC")
        else:
            recorded=recorded.tz_convert("UTC")

        start_day=recorded.normalize().tz_localize(None)
        for horizon in horizons:
            key=(int(decision["id"]),int(horizon))
            if key in existing:
                continue
            due_day=start_day + pd.offsets.BDay(int(horizon))
            due=pd.Timestamp(due_day).tz_localize("UTC")
            if now.normalize() >= due:
                rows.append({
                    "forward_test_id":int(decision["id"]),
                    "ticker":str(decision["ticker"]),
                    "decision":str(decision["decision"]),
                    "recorded_at":recorded.isoformat(),
                    "horizon_days":int(horizon),
                    "due_date":due.date().isoformat(),
                })
    return pd.DataFrame(rows)


class YFinanceForwardMarketData:
    """Small yfinance adapter isolated so outcome logic stays testable."""

    def __init__(self, benchmark_ticker="SPY"):
        self.benchmark_ticker=benchmark_ticker.upper().strip()

    @staticmethod
    def _yf():
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError(
                "yfinance is required for automatic forward-test updates."
            ) from exc
        return yf

    def close_on_or_after(self,ticker,date,max_calendar_days=7):
        yf=self._yf()
        start=pd.Timestamp(date).date()
        end=(pd.Timestamp(date)+pd.Timedelta(days=max_calendar_days+1)).date()
        data=yf.download(
            ticker,
            start=str(start),
            end=str(end),
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        if data is None or data.empty:
            raise ValueError(f"No market data found for {ticker} on/after {start}.")
        close=data["Close"]
        if isinstance(close,pd.DataFrame):
            close=close.iloc[:,0]
        close=pd.to_numeric(close,errors="coerce").dropna()
        if close.empty:
            raise ValueError(f"No closing price found for {ticker} on/after {start}.")
        return float(close.iloc[0]),pd.Timestamp(close.index[0]).date().isoformat()

    def benchmark_return(self,recorded_at,due_date):
        entry,_=self.close_on_or_after(
            self.benchmark_ticker,pd.Timestamp(recorded_at).date())
        observed,observed_date=self.close_on_or_after(
            self.benchmark_ticker,due_date)
        result=((observed-entry)/entry)*100.0
        return entry,observed,result,observed_date


def update_due_forward_outcomes(
    *,
    db_path="data/paper_trading.db",
    account_id,
    market_data=None,
    benchmark_ticker="SPY",
    now=None,
):
    """Populate all currently due forward-test observations."""
    decisions_repo=ForwardTestRepository(db_path)
    outcomes_repo=ForwardTestOutcomeRepository(db_path)
    decisions=decisions_repo.history(account_id)
    current=outcomes_repo.outcomes(account_id)
    due=due_forward_test_observations(decisions,current,now=now)

    if due.empty:
        return {"due":0,"updated":0,"failed":[]}

    market_data=market_data or YFinanceForwardMarketData(benchmark_ticker)
    updated=0
    failed=[]

    for _,item in due.iterrows():
        try:
            stock_price,stock_date=market_data.close_on_or_after(
                item["ticker"],item["due_date"])
            benchmark_entry,benchmark_price,benchmark_return,_ = (
                market_data.benchmark_return(
                    item["recorded_at"],item["due_date"])
            )

            # Save normal outcome first.
            outcomes_repo.save_outcome(
                forward_test_id=int(item["forward_test_id"]),
                horizon_days=int(item["horizon_days"]),
                observed_price=stock_price,
                observed_at=stock_date,
            )

            with outcomes_repo.database.connect() as c:
                row=c.execute(
                    """SELECT return_pct FROM paper_forward_test_outcomes
                    WHERE forward_test_id=? AND horizon_days=?""",
                    (int(item["forward_test_id"]),int(item["horizon_days"])),
                ).fetchone()
                stock_return=(
                    float(row["return_pct"])
                    if row is not None and row["return_pct"] is not None
                    else None
                )
                excess=(
                    stock_return-benchmark_return
                    if stock_return is not None else None
                )
                c.execute(
                    """UPDATE paper_forward_test_outcomes SET
                    benchmark_ticker=?,
                    benchmark_entry_price=?,
                    benchmark_observed_price=?,
                    benchmark_return_pct=?,
                    excess_return_pct=?
                    WHERE forward_test_id=? AND horizon_days=?""",
                    (
                        market_data.benchmark_ticker,
                        benchmark_entry,
                        benchmark_price,
                        benchmark_return,
                        excess,
                        int(item["forward_test_id"]),
                        int(item["horizon_days"]),
                    ),
                )
            updated+=1
        except Exception as exc:
            failed.append({
                "forward_test_id":int(item["forward_test_id"]),
                "ticker":item["ticker"],
                "horizon_days":int(item["horizon_days"]),
                "error":str(exc),
            })

    return {"due":len(due),"updated":updated,"failed":failed}


def benchmark_comparison(frame):
    if frame is None or frame.empty or "excess_return_pct" not in frame:
        return pd.DataFrame()
    d=frame.copy()
    d["excess_return_pct"]=pd.to_numeric(
        d["excess_return_pct"],errors="coerce")
    d=d.dropna(subset=["excess_return_pct"])
    if d.empty:return pd.DataFrame()
    rows=[]
    for (horizon,decision),g in d.groupby(["horizon_days","decision"]):
        rows.append({
            "Horizon Days":int(horizon),
            "Decision":str(decision),
            "Observations":len(g),
            "Avg Excess Return":float(g["excess_return_pct"].mean()),
            "Beat Benchmark Rate":float((g["excess_return_pct"]>0).mean()),
        })
    return pd.DataFrame(rows).sort_values(
        ["Horizon Days","Decision"]).reset_index(drop=True)
