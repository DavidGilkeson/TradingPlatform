from types import SimpleNamespace
from paper_trading.dashboard_summary import build_command_centre_summary, next_action_text


def test_command_centre_summary_combines_account_and_today_activity():
    snap = SimpleNamespace(cash=60000, positions_value=40000, equity=100000,
                           unrealised_pnl=500, realised_pnl=250,
                           total_return_pct=.0075, open_positions=2)
    trades = [
        {"exit_date":"2026-09-18T10:00:00+00:00", "realised_pnl":125},
        {"exit_date":"2026-09-18", "realised_pnl":-25},
        {"exit_date":"2026-09-17", "realised_pnl":150},
    ]
    out = build_command_centre_summary(snapshot=snap, positions=[1,2], trades=trades, today="2026-09-18")
    assert out["equity"] == 100000
    assert out["total_pnl"] == 750
    assert out["today_completed_trades"] == 2
    assert out["today_realised_pnl"] == 100
    assert out["cash_pct"] == .6
    assert out["invested_pct"] == .4


def test_command_centre_summary_handles_zero_equity():
    snap = SimpleNamespace(cash=0, positions_value=0, equity=0,
                           unrealised_pnl=0, realised_pnl=0,
                           total_return_pct=0, open_positions=0)
    out = build_command_centre_summary(snapshot=snap, positions=[], trades=[], today="2026-09-18")
    assert out["cash_pct"] == 0
    assert out["invested_pct"] == 0


def test_next_action_copy_is_specific_to_lifecycle():
    assert "scanner" in next_action_text({"next_stage":"Find Opportunity"}).lower()
    assert "monitor" in next_action_text({"next_stage":"Completed Trade"}).lower()
    assert "complete" in next_action_text({"next_stage":"Cycle complete"}).lower()
