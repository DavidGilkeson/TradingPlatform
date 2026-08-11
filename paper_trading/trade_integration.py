from __future__ import annotations
import pandas as pd

def prepare_quick_trade_candidates(frame, minimum_score=None, limit=10):
    if frame is None or frame.empty or "Ticker" not in frame.columns:
        return pd.DataFrame()
    result=frame.copy()
    result["Ticker"]=result["Ticker"].astype(str).str.upper().str.strip()
    result=result[result["Ticker"]!=""].drop_duplicates("Ticker",keep="first")
    score_col=next((c for c in ("Atlas Score","Score") if c in result.columns),None)
    if score_col:
        result[score_col]=pd.to_numeric(result[score_col],errors="coerce")
        if minimum_score is not None:
            result=result[result[score_col].fillna(float("-inf"))>=minimum_score]
        result=result.sort_values(score_col,ascending=False,na_position="last")
    return result.head(max(int(limit),1)).reset_index(drop=True)

def trade_candidate_summary(row):
    data=row.to_dict() if isinstance(row,pd.Series) else dict(row)
    return {
        "ticker":str(data.get("Ticker",data.get("ticker",""))).upper().strip(),
        "score":data.get("Atlas Score",data.get("Score")),
        "verdict":data.get("Atlas Verdict",data.get("Signal","")),
        "confidence":data.get("Atlas Confidence",data.get("Confidence")),
    }
