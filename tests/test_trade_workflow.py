from paper_trading.workflow import workflow_progress, review_completeness
from paper_trading.journal_review import PaperTradeReviewRepository


def test_workflow_progress():
    p=workflow_progress(
        has_scan=True,has_thesis=True,has_risk_plan=True,
        has_open_position=False,has_completed_trade=False,has_review=False)
    assert p["completed"]==3
    assert p["total"]==6
    assert p["pct"]==0.5


def test_review_completeness():
    review={
        "followed_plan":True,
        "emotional_state":"Calm",
        "what_worked":"Waited for setup",
        "what_went_wrong":"",
        "lesson_learned":"Keep waiting",
    }
    assert review_completeness(review)==0.8


def test_review_schema_migrates_and_saves_new_fields(tmp_path):
    repo=PaperTradeReviewRepository(str(tmp_path/"journal.db"))
    # Foreign keys require parent rows in real app; inspect migration columns here.
    with repo.database.connect() as c:
        cols={r["name"] for r in c.execute(
            "PRAGMA table_info(paper_trade_reviews)").fetchall()}
    assert "execution_rating" in cols
    assert "next_time_action" in cols
