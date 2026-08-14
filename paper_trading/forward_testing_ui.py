"""Forward Testing workspace."""
import streamlit as st
from .account import PaperAccountService
from .forward_testing import (
    ForwardTestRepository,
    ForwardTestOutcomeRepository,
    forward_test_summary,
    outcome_comparison,
    decision_quality,
    due_forward_test_observations,
    update_due_forward_outcomes,
    benchmark_comparison,
)

def display_forward_testing(*,db_path="data/paper_trading.db"):
    st.subheader("🧪 Forward Testing")
    st.caption("Record Atlas opportunities prospectively before their outcomes are known.")
    service=PaperAccountService(db_path); account=service.active_account()
    repo=ForwardTestRepository(db_path)

    with st.expander("Record Forward-Test Decision",expanded=True):
        a,b=st.columns(2)
        with a:
            ticker=st.text_input("Ticker",key="ft_ticker").upper().strip()
            decision=st.selectbox("Decision",["WATCH","TAKEN","SKIPPED"],key="ft_decision")
            score=st.number_input("Atlas Score",0.0,100.0,70.0,1.0,key="ft_score")
        with b:
            confidence=st.number_input("Confidence",0.0,10.0,5.0,1.0,key="ft_confidence")
            price=st.number_input("Market Price",min_value=0.0,value=0.0,step=0.01,key="ft_price")
            signal=st.text_input("Signal",key="ft_signal")
        regime_cols=st.columns(2)
        with regime_cols[0]:
            market_regime=st.selectbox(
                "Market Regime",["Unknown","Bullish","Neutral","Bearish"],
                key="ft_market_regime")
        with regime_cols[1]:
            volatility_regime=st.selectbox(
                "Volatility Regime",["Unknown","Quiet","Normal","Volatile"],
                key="ft_volatility_regime")
        reason=st.text_area("Why take, skip or watch this setup?",key="ft_reason")
        if st.button("Save Forward-Test Decision",type="primary",key="ft_save"):
            if not ticker: st.error("Enter a ticker first.")
            else:
                repo.record(account_id=account.id,ticker=ticker,decision=decision,
                    atlas_score=score,confidence=confidence,
                    market_price=price if price>0 else None,
                    signal=signal or None,reason=reason or None,
                    market_regime=None if market_regime=="Unknown" else market_regime,
                    volatility_regime=None if volatility_regime=="Unknown" else volatility_regime)
                st.success(f"{ticker} recorded as {decision}."); st.rerun()

    history=repo.history(account.id); x=forward_test_summary(history)
    cols=st.columns(5)
    cols[0].metric("Recorded",x["total"]); cols[1].metric("Taken",x["taken"])
    cols[2].metric("Skipped",x["skipped"]); cols[3].metric("Watching",x["watch"])
    cols[4].metric("Decision Discipline","—" if x["discipline_rate"] is None else f'{x["discipline_rate"]*100:.1f}%')
    if history.empty: st.info("No forward-test decisions recorded yet.")
    else: st.dataframe(history,width="stretch",hide_index=True)
    st.warning("Record opportunities before you know their outcome to reduce hindsight and selection bias.")


    st.divider()
    st.markdown("### 📍 Outcome Tracking")
    outcome_repo = ForwardTestOutcomeRepository(db_path)
    existing_outcomes = outcome_repo.outcomes(account.id)
    due = due_forward_test_observations(history, existing_outcomes)

    auto_cols = st.columns([2, 1])
    auto_cols[0].metric("Due Automatic Observations", len(due))
    if auto_cols[1].button(
        "Update Due Outcomes",
        type="primary",
        key="ft_auto_update",
        disabled=due.empty,
    ):
        with st.spinner("Downloading due stock and SPY benchmark prices..."):
            result = update_due_forward_outcomes(
                db_path=db_path,
                account_id=account.id,
                benchmark_ticker="SPY",
            )
        if result["updated"]:
            st.success(
                f'Updated {result["updated"]} of {result["due"]} due observations.'
            )
        if result["failed"]:
            st.warning(
                f'{len(result["failed"])} observation(s) could not be updated.'
            )
            st.dataframe(result["failed"],width="stretch",hide_index=True)
        if not result["updated"] and not result["failed"]:
            st.info("No observations are due yet.")
        st.rerun()

    st.caption(
        "Automatic updates use the first available market close on or after "
        "each due business-day horizon and compare the stock with SPY."
    )

    if history.empty:
        st.info("Record a forward-test decision before adding outcomes.")
    else:
        labels = {
            int(row["id"]): (
                f'#{int(row["id"])} · {row["ticker"]} · '
                f'{row["decision"]} · {row["recorded_at"]}'
            )
            for _, row in history.iterrows()
        }

        decision_id = st.selectbox(
            "Forward-test decision",
            options=list(labels.keys()),
            format_func=lambda value: labels[value],
            key="ft_outcome_decision",
        )

        c1, c2 = st.columns(2)
        with c1:
            horizon = st.selectbox(
                "Outcome horizon",
                [1, 3, 5, 10, 20],
                index=2,
                format_func=lambda value: f"{value} trading day(s)",
                key="ft_outcome_horizon",
            )
        with c2:
            observed_price = st.number_input(
                "Observed Price",
                min_value=0.0,
                value=0.0,
                step=0.01,
                key="ft_observed_price",
            )

        if st.button("Save Outcome", key="ft_save_outcome"):
            if observed_price <= 0:
                st.error("Observed price must be greater than zero.")
            else:
                outcome_repo.save_outcome(
                    forward_test_id=decision_id,
                    horizon_days=horizon,
                    observed_price=observed_price,
                )
                st.success("Forward-test outcome saved.")
                st.rerun()

    outcomes = outcome_repo.outcomes(account.id)

    if not outcomes.empty:
        st.markdown("#### Taken vs Skipped")
        comparison = outcome_comparison(outcomes)
        st.dataframe(
            comparison,
            width="stretch",
            hide_index=True,
            column_config={
                "Positive Rate": st.column_config.NumberColumn(format="%.2f"),
                "Average Return": st.column_config.NumberColumn(format="%.2f%%"),
                "Median Return": st.column_config.NumberColumn(format="%.2f%%"),
                "Best Return": st.column_config.NumberColumn(format="%.2f%%"),
                "Worst Return": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )

        available_horizons = sorted(
            int(value) for value in outcomes["horizon_days"].unique()
        )
        selected_horizon = st.selectbox(
            "Decision-quality horizon",
            available_horizons,
            format_func=lambda value: f"{value} trading day(s)",
            key="ft_quality_horizon",
        )

        quality = decision_quality(outcomes, selected_horizon)

        if quality is None:
            st.info(
                "Atlas needs both TAKEN and SKIPPED outcomes at this horizon "
                "before it can measure decision edge."
            )
        else:
            metrics = st.columns(3)
            metrics[0].metric(
                "Taken Avg Return",
                f'{quality["taken_average_return"]:.2f}%',
            )
            metrics[1].metric(
                "Skipped Avg Return",
                f'{quality["skipped_average_return"]:.2f}%',
            )
            metrics[2].metric(
                "Decision Edge",
                f'{quality["decision_edge"]:+.2f}%',
            )

            if quality["decision_edge"] > 0:
                st.success(
                    "At this horizon, TAKEN opportunities have outperformed "
                    "SKIPPED opportunities so far."
                )
            elif quality["decision_edge"] < 0:
                st.warning(
                    "At this horizon, SKIPPED opportunities have outperformed "
                    "TAKEN opportunities so far."
                )
            else:
                st.info(
                    "Taken and skipped opportunities currently have the same "
                    "average return at this horizon."
                )

        benchmark = benchmark_comparison(outcomes)
        st.markdown("#### Benchmark-Relative Performance")
        if benchmark.empty:
            st.info(
                "Automatic SPY benchmark data will appear after due outcomes "
                "have been updated."
            )
        else:
            st.dataframe(
                benchmark,
                width="stretch",
                hide_index=True,
                column_config={
                    "Avg Excess Return": st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),
                    "Beat Benchmark Rate": st.column_config.NumberColumn(
                        format="%.2f"
                    ),
                },
            )

        st.markdown("#### Recorded Outcomes")
        st.dataframe(outcomes, width="stretch", hide_index=True)
