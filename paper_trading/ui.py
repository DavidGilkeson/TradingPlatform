from __future__ import annotations
import pandas as pd
from .scan_feed import resolve_streamlit_scan
from .workflow import workflow_progress
from .journal_review import PaperTradeReviewRepository
import streamlit as st
from .sprint_status_ui import display_paper_trading_system_status
from .account import PaperAccountService
from .journal_ui import display_paper_journal_dashboard
from .performance_ui import display_performance_dashboard
from .risk_ui import display_risk_manager
from .guardrails_ui import display_portfolio_guardrails
from .exit_plans_ui import display_exit_plan_manager
from .auto_exits_ui import display_automatic_exit_controls
from .trading_intelligence_ui import display_trading_intelligence
from .regime_intelligence_ui import display_regime_intelligence
from .setup_intelligence_ui import display_setup_intelligence
from .outcome_calibration_ui import display_outcome_calibration
from .intelligence_health_ui import display_intelligence_health
from .forward_testing_ui import display_forward_testing
from .forward_validation_ui import display_forward_validation
from .cohort_validation_ui import display_cohort_validation
from .portfolio_ui import display_live_portfolio_dashboard
from .trading_ui import display_order_history, display_order_ticket

def display_paper_trading_dashboard(db_path="data/paper_trading.db", market_df: pd.DataFrame | None=None):
    # Recover the canonical/current scan even when older app.py versions
    # forget to pass market_df into this dashboard after a Streamlit rerun.
    market_df = resolve_streamlit_scan(market_df)
    st.header("💼 Atlas Paper Trading")

    # Sprint 33: lightweight end-to-end workflow status.
    try:
        account_service=PaperAccountService(db_path)
        active_account=account_service.active_account()
        positions=account_service.repository.list_positions(active_account.id)
        trades=account_service.repository.list_trades(active_account.id)
        review_repo=PaperTradeReviewRepository(db_path)
        latest_review=(
            review_repo.get_review(int(trades[0].id))
            if trades
            else None
        )
        progress=workflow_progress(
            has_scan=market_df is not None and not market_df.empty,
            has_thesis=False,
            has_risk_plan=False,
            has_open_position=bool(positions),
            has_completed_trade=bool(trades),
            has_review=bool(latest_review),
        )
        st.progress(
            progress["pct"],
            text=(
                f'Paper-trading workflow: {progress["completed"]}/'
                f'{progress["total"]} stages completed'
            ),
        )
        st.caption(
            "Scanner → Thesis → Risk Plan → Paper Position → "
            "Completed Trade → Review"
        )
    except Exception:
        pass
    service = PaperAccountService(db_path)
    account = service.initialise_account()

    if market_df is not None and not market_df.empty and "Ticker" in market_df.columns:
        price_col = next((c for c in ("Close","Current Price","Price") if c in market_df.columns), None)
        if price_col:
            prices = dict(zip(
                market_df["Ticker"].astype(str).str.upper(),
                pd.to_numeric(market_df[price_col], errors="coerce"),
            ))
            service.update_market_prices({
                t: float(p) for t,p in prices.items() if pd.notna(p) and float(p) > 0
            })

    trade_tab, portfolio_tab, forward_tab, intelligence_tab, history_tab, account_tab = st.tabs(
        ["🛒 Trade","📊 Portfolio","🧪 Forward Test","🧠 Intelligence","📋 History","⚙ Account"]
    )
    with trade_tab:
        display_order_ticket(market_df=market_df, db_path=db_path)
    with portfolio_tab:
        display_live_portfolio_dashboard(db_path=db_path)
    with forward_tab:
        display_forward_testing(db_path=db_path)

    with intelligence_tab:
        intelligence_sections = st.tabs([
            "❤️ Health",
            "🏁 Validation",
            "🔬 Cohorts",
            "📈 Performance",
            "🧠 Patterns",
            "🌦️ Regimes",
            "🧩 Setups",
            "🎯 Calibration",
            "📓 Journal",
        ])
        with intelligence_sections[0]:
            display_intelligence_health(db_path=db_path)
        with intelligence_sections[1]:
            display_forward_validation(db_path=db_path)
        with intelligence_sections[2]:
            display_cohort_validation(db_path=db_path)
        with intelligence_sections[3]:
            display_performance_dashboard(db_path=db_path)
        with intelligence_sections[4]:
            display_trading_intelligence(db_path=db_path)
        with intelligence_sections[5]:
            display_regime_intelligence(db_path=db_path)
        with intelligence_sections[6]:
            display_setup_intelligence(db_path=db_path)
        with intelligence_sections[7]:
            display_outcome_calibration(db_path=db_path)
        with intelligence_sections[8]:
            display_paper_journal_dashboard(db_path=db_path)

    with history_tab:
        display_order_history(db_path=db_path)
    with account_tab:
        account = service.active_account()
        snap = service.snapshot(persist=True)
        cols = st.columns(4)
        for col,(label,value) in zip(cols,[
            ("Starting Balance",f"${account.starting_balance:,.2f}"),
            ("Current Equity",f"${snap.equity:,.2f}"),
            ("Cash",f"${snap.cash:,.2f}"),
            ("Total Return",f"{snap.total_return_pct:.2%}"),
        ]):
            col.metric(label,value)
        with st.expander("Reset Paper Account", expanded=True):
            balance = st.number_input("New starting balance", min_value=100.0, value=float(account.starting_balance), step=1000.0)
            confirm = st.text_input('Type "RESET" to confirm')
            if st.button("Reset Paper Account"):
                if confirm != "RESET":
                    st.error('Type "RESET" exactly.')
                else:
                    service.reset_account(account.name, balance)
                    st.success("Paper account reset.")
                    st.rerun()
