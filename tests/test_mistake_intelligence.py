import pandas as pd
from paper_trading.mistake_intelligence import (
    detect_mistakes,mistake_summary,recurring_lessons)

def test_detects_common_mistakes():
    found=detect_mistakes("I had FOMO, chased the entry and then ignored my stop.")
    assert "FOMO / chased entry" in found
    assert "Broke stop / risk rule" in found

def test_detects_emotional_decision():
    assert "Emotional decision" in detect_mistakes("I panic sold and was impatient.")

def test_summary_ranks_costliest_pattern():
    frame=pd.DataFrame([
      {"mistake":"FOMO / chased entry","realised_pnl":-100,"return_pct":-5},
      {"mistake":"FOMO / chased entry","realised_pnl":-50,"return_pct":-2},
      {"mistake":"Exited too early","realised_pnl":20,"return_pct":1},
    ])
    table=mistake_summary(frame)
    assert table.iloc[0]["Mistake"]=="FOMO / chased entry"
    assert table.iloc[0]["Net P&L"]==-150
    assert table.iloc[0]["Occurrences"]==2

def test_recurring_lessons_are_deduplicated():
    frame=pd.DataFrame([
      {"next_time_action":"Wait for confirmation","lesson_learned":"Use stops"},
      {"next_time_action":"wait for confirmation","lesson_learned":"Size smaller"},
    ])
    lessons=recurring_lessons(frame)
    assert lessons.count("Wait for confirmation")==1
    assert "Use stops" in lessons

def test_empty_text_safe():
    assert detect_mistakes("")==[]
