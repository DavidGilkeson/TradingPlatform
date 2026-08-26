"""Structured behavioural mistake and lesson intelligence."""

from __future__ import annotations
import re
import pandas as pd
from .database import PaperTradingDatabase

MISTAKE_RULES={
 "FOMO / chased entry":(r"\bfomo\b",r"\bchased?\b",r"\btoo late\b"),
 "Entered too early":(r"\btoo early\b",r"\bentered early\b",r"\bjumped in\b"),
 "Broke stop / risk rule":(
     r"\bignored (?:my |the )?stop\b",r"\bmoved (?:my )?stop\b",
     r"\bno stop\b",r"\bheld past stop\b",r"\bbroke (?:my )?risk\b"),
 "Poor risk/reward":(
     r"\bpoor r[:/ ]?r\b",r"\brisk.?reward\b",r"\btoo much risk\b"),
 "Oversized position":(r"\boversiz",r"\btoo (?:big|large)\b",r"\bposition too\b"),
 "Exited too early":(
     r"\bexited early\b",r"\bsold early\b",r"\btook profit too early\b"),
 "Held too long":(r"\bheld too long\b",r"\bdidn.?t take profit\b",r"\bgave back\b"),
 "Traded against plan":(
     r"\bbroke (?:the|my) plan\b",r"\bignored (?:the|my) plan\b",
     r"\bagainst (?:the|my) plan\b"),
 "Emotional decision":(
     r"\bemotional\b",r"\bpanic",r"\brevenge\b",r"\bgreed",r"\bimpatient\b"),
}

def detect_mistakes(text):
    value=str(text or "").lower().strip()
    if not value: return []
    return [
        label for label,patterns in MISTAKE_RULES.items()
        if any(re.search(pattern,value,re.I) for pattern in patterns)
    ]

def build_mistake_frame(db_path="data/paper_trading.db",account_id=None):
    db=PaperTradingDatabase(db_path)
    where="WHERE t.account_id=?" if account_id is not None else ""
    params=(account_id,) if account_id is not None else ()
    with db.connect() as c:
        reviews=pd.read_sql_query(f"""
            SELECT t.id AS trade_id,t.ticker,t.realised_pnl,t.return_pct,
                   r.followed_plan,r.execution_rating,r.what_went_wrong,
                   r.lesson_learned,r.next_time_action
            FROM paper_trades t
            JOIN paper_trade_reviews r ON r.trade_id=t.id
            {where}
            ORDER BY t.exit_date DESC,t.id DESC
        """,c,params=params)
    rows=[]
    for review in reviews.to_dict("records"):
        mistakes=detect_mistakes(review.get("what_went_wrong"))
        if not mistakes and review.get("followed_plan")==0:
            mistakes=["Traded against plan"]
        for mistake in mistakes:
            rows.append({
                "trade_id":review["trade_id"],"ticker":review["ticker"],
                "mistake":mistake,"realised_pnl":review["realised_pnl"],
                "return_pct":review["return_pct"],
                "execution_rating":review["execution_rating"],
                "lesson_learned":review["lesson_learned"],
                "next_time_action":review["next_time_action"],
            })
    return pd.DataFrame(rows)

def mistake_summary(frame):
    if frame is None or frame.empty: return pd.DataFrame()
    rows=[]
    for mistake,g in frame.groupby("mistake"):
        pnl=pd.to_numeric(g["realised_pnl"],errors="coerce").dropna()
        ret=pd.to_numeric(g["return_pct"],errors="coerce").dropna()
        rows.append({
            "Mistake":mistake,"Occurrences":len(g),
            "Net P&L":float(pnl.sum()) if not pnl.empty else 0.0,
            "Average Return":float(ret.mean()) if not ret.empty else None,
            "Loss Rate":float((pnl<0).mean()) if not pnl.empty else None,
        })
    return pd.DataFrame(rows).sort_values(
        ["Net P&L","Occurrences"],ascending=[True,False]).reset_index(drop=True)

def recurring_lessons(frame,limit=5):
    if frame is None or frame.empty: return []
    lessons=[]; seen=set()
    for column in ("next_time_action","lesson_learned"):
        if column not in frame: continue
        for value in frame[column].dropna().astype(str):
            clean=value.strip(); key=clean.lower()
            if clean and key not in seen:
                seen.add(key); lessons.append(clean)
                if len(lessons)>=limit: return lessons
    return lessons
