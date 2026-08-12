"""Interactive BUY and SELL ticket for Atlas paper trading."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from .account import PaperAccountService
from .one_click import (
    clear_paper_trade_intent,
    consume_paper_trade_intent,
)
from .orders import PaperOrderService
from .portfolio_guardrails import (
    GuardrailSettings,
    evaluate_proposed_buy_guardrails,
)
from .risk_manager import calculate_position_size, validate_order_risk


def _latest_price(
    ticker: str,
    market_df: pd.DataFrame | None,
) -> float | None:
    if market_df is None or market_df.empty or "Ticker" not in market_df.columns:
        return None

    rows = market_df.loc[
        market_df["Ticker"].astype(str).str.upper() == ticker.upper()
    ]

    if rows.empty:
        return None

    row = rows.iloc[0]

    for column in ("Close", "Current Price", "Price", "Latest Price"):
        if column in row.index:
            try:
                value = float(row[column])
                if pd.notna(value) and value > 0:
                    return value
            except (TypeError, ValueError):
                continue

    return None


def _stock_context(
    ticker: str,
    market_df: pd.DataFrame | None,
) -> dict[str, Any]:
    if market_df is None or market_df.empty or "Ticker" not in market_df.columns:
        return {}

    rows = market_df.loc[
        market_df["Ticker"].astype(str).str.upper() == ticker.upper()
    ]
    return rows.iloc[0].to_dict() if not rows.empty else {}


def _apply_suggested_shares(value: float) -> None:
    """Safely update the Shares widget from a Streamlit callback."""

    st.session_state["paper_order_shares"] = float(value)


def display_order_ticket(
    *,
    market_df: pd.DataFrame | None = None,
    db_path: str = "data/paper_trading.db",
) -> None:
    """Display a market order ticket with risk controls."""

    st.subheader("🛒 Paper Order Ticket")

    account_service = PaperAccountService(db_path)
    account = account_service.initialise_account()

    tickers: list[str] = []
    if (
        market_df is not None
        and not market_df.empty
        and "Ticker" in market_df.columns
    ):
        tickers = sorted(
            market_df["Ticker"]
            .dropna()
            .astype(str)
            .str.upper()
            .unique()
            .tolist()
        )

    intent = consume_paper_trade_intent()
    intent_ticker = intent.get("ticker") if intent else None

    if intent_ticker and intent_ticker not in tickers:
        tickers = [intent_ticker] + tickers

    ticker_options = tickers or ["AAPL"]

    default_index = 0
    if intent_ticker and intent_ticker in ticker_options:
        default_index = ticker_options.index(intent_ticker)

    ticker = st.selectbox(
        "Ticker",
        options=ticker_options,
        index=default_index,
        key="paper_order_ticker",
    )

    position_map = {
        position.ticker: position
        for position in account_service.repository.list_positions(account.id)
    }
    current_position = position_map.get(ticker)

    suggested_price = _latest_price(ticker, market_df)
    if suggested_price is None:
        suggested_price = (
            current_position.current_price
            if current_position is not None
            else 100.0
        )

    context = _stock_context(ticker, market_df)

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Market Price", f"${suggested_price:,.2f}")
    metric2.metric("Cash", f"${account.cash:,.2f}")
    metric3.metric(
        "Shares Held",
        f"{current_position.shares:,.4f}" if current_position else "0",
    )
    metric4.metric(
        "Atlas Verdict",
        str(context.get("Atlas Verdict", context.get("Signal", "—"))),
    )

    ticket_col, settings_col = st.columns([1.5, 1])

    with settings_col:
        commission = st.number_input(
            "Commission per order",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="paper_commission",
        )
        slippage_pct = st.number_input(
            "Slippage (%)",
            min_value=0.0,
            value=0.10,
            step=0.05,
            key="paper_slippage_pct",
        ) / 100

    with ticket_col:
        default_side = (
            intent.get("side", "BUY")
            if intent
            else "BUY"
        )

        side = st.radio(
            "Side",
            ["BUY", "SELL"],
            index=0 if default_side == "BUY" else 1,
            horizontal=True,
            key="paper_order_side",
        )

        default_shares = (
            float(intent.get("shares", 1.0))
            if intent
            else 1.0
        )

        shares = st.number_input(
            "Shares",
            min_value=0.0001,
            value=max(default_shares, 0.0001),
            step=1.0,
            format="%.4f",
            key="paper_order_shares",
        )

        market_price = st.number_input(
            "Execution reference price",
            min_value=0.01,
            value=float(suggested_price),
            step=0.01,
            format="%.2f",
            key=f"paper_market_price_{ticker}",
        )

        default_reason = (
            str(intent.get("reason", ""))
            if intent
            else str(context.get("Atlas Verdict", ""))
        )

        risk_plan = None
        risk_decision = None

        if side == "BUY":
            st.markdown("#### 🛡️ Risk Controls")

            risk_col1, risk_col2, risk_col3 = st.columns(3)

            with risk_col1:
                risk_pct = st.number_input(
                    "Risk per trade (%)",
                    min_value=0.1,
                    max_value=10.0,
                    value=1.0,
                    step=0.1,
                    key="paper_risk_pct",
                )

            with risk_col2:
                max_position_pct = st.number_input(
                    "Max position (%)",
                    min_value=1.0,
                    max_value=100.0,
                    value=20.0,
                    step=1.0,
                    key="paper_risk_max_position",
                )

            with risk_col3:
                minimum_rr = st.number_input(
                    "Min reward/risk",
                    min_value=0.5,
                    max_value=10.0,
                    value=2.0,
                    step=0.25,
                    key="paper_risk_min_rr",
                )

            default_stop = max(0.01, market_price * 0.95)
            default_target = market_price * 1.10

            stop_price = st.number_input(
                "Stop-loss price",
                min_value=0.01,
                value=float(default_stop),
                step=0.01,
                format="%.2f",
                key="paper_risk_stop",
            )

            target_price = st.number_input(
                "Take-profit target",
                min_value=0.01,
                value=float(default_target),
                step=0.01,
                format="%.2f",
                key="paper_risk_target",
            )

            try:
                snapshot = account_service.snapshot(persist=False)

                risk_plan = calculate_position_size(
                    account_equity=float(snapshot.equity),
                    entry_price=float(market_price),
                    stop_price=float(stop_price),
                    target_price=float(target_price),
                    risk_pct=float(risk_pct),
                    max_position_pct=float(max_position_pct),
                )

                risk_decision = validate_order_risk(
                    account_equity=float(snapshot.equity),
                    cash=float(account.cash),
                    shares=float(shares),
                    entry_price=float(market_price),
                    stop_price=float(stop_price),
                    target_price=float(target_price),
                    risk_pct_limit=float(risk_pct),
                    max_position_pct=float(max_position_pct),
                    minimum_reward_risk=float(minimum_rr),
                )

            except ValueError as error:
                st.error(str(error))

            else:
                risk_metrics = st.columns(4)

                risk_metrics[0].metric(
                    "Suggested Shares",
                    f"{risk_plan.recommended_shares:,}",
                )
                risk_metrics[1].metric(
                    "Max $ Risk",
                    f"${risk_plan.max_risk_amount:,.2f}",
                )
                risk_metrics[2].metric(
                    "Risk / Share",
                    f"${risk_plan.risk_per_share:,.2f}",
                )
                risk_metrics[3].metric(
                    "Reward / Risk",
                    (
                        "—"
                        if risk_plan.reward_risk_ratio is None
                        else f"{risk_plan.reward_risk_ratio:.2f}:1"
                    ),
                )

                if risk_plan.recommended_shares > 0:
                    st.button(
                        "Use Suggested Position Size",
                        key="paper_use_risk_size",
                        width="stretch",
                        on_click=_apply_suggested_shares,
                        args=(float(risk_plan.recommended_shares),),
                    )

                if risk_decision.allowed:
                    st.success(
                        "Risk check passed for this simulated BUY order."
                    )
                else:
                    for blocker in risk_decision.blockers:
                        st.error(blocker)

                for warning in risk_decision.warnings:
                    st.warning(warning)


        guardrail_status = None

        if side == "BUY":
            st.markdown("#### 🚦 Portfolio Guardrails")

            g1, g2 = st.columns(2)

            with g1:
                guardrail_max_exposure = st.number_input(
                    "Max total exposure (%)",
                    min_value=10.0,
                    max_value=100.0,
                    value=80.0,
                    step=5.0,
                    key="paper_guardrail_max_exposure",
                )

                guardrail_max_positions = st.number_input(
                    "Max open positions",
                    min_value=1,
                    max_value=50,
                    value=8,
                    step=1,
                    key="paper_guardrail_max_positions",
                )

            with g2:
                guardrail_daily_loss = st.number_input(
                    "Daily loss limit (%)",
                    min_value=0.5,
                    max_value=20.0,
                    value=3.0,
                    step=0.5,
                    key="paper_guardrail_daily_loss",
                )

                guardrail_loss_streak = st.number_input(
                    "Consecutive-loss pause",
                    min_value=1,
                    max_value=20,
                    value=3,
                    step=1,
                    key="paper_guardrail_loss_streak",
                )

            settings = GuardrailSettings(
                max_total_exposure_pct=float(guardrail_max_exposure),
                max_open_positions=int(guardrail_max_positions),
                daily_loss_limit_pct=float(guardrail_daily_loss),
                consecutive_loss_limit=int(guardrail_loss_streak),
            )

            guardrail_status = evaluate_proposed_buy_guardrails(
                account_service,
                ticker=ticker,
                proposed_position_value=float(shares) * float(market_price),
                settings=settings,
            )

            guardrail_metrics = st.columns(2)
            guardrail_metrics[0].metric(
                "Projected Exposure",
                f"{guardrail_status.projected_exposure_pct:.1f}%",
            )
            guardrail_metrics[1].metric(
                "Projected Open Positions",
                guardrail_status.projected_open_positions,
            )

            if guardrail_status.allowed:
                st.success("Portfolio guardrail check passed.")
            else:
                for blocker in guardrail_status.blockers:
                    st.error(blocker)

            for warning in guardrail_status.warnings:
                st.warning(warning)

        reason = st.text_input(
            "Trade reason",
            value=default_reason,
            placeholder="Example: Atlas Strong Buy",
            key="paper_trade_reason",
        )

        notes = st.text_area(
            "Notes",
            value=(
                str(intent.get("notes", ""))
                if intent
                else ""
            ),
            placeholder="Why are you taking this trade?",
            key="paper_trade_notes",
        )

        confidence = st.slider(
            "Confidence",
            min_value=1,
            max_value=10,
            value=5,
            key="paper_trade_confidence",
        )

        estimated_price = (
            market_price * (1 + slippage_pct)
            if side == "BUY"
            else market_price * (1 - slippage_pct)
        )
        estimated_value = shares * estimated_price
        estimated_total = (
            estimated_value + commission
            if side == "BUY"
            else estimated_value - commission
        )

        st.caption(
            f"Estimated fill: ${estimated_price:,.2f} · "
            f"{'Total cost' if side == 'BUY' else 'Net proceeds'}: "
            f"${estimated_total:,.2f}"
        )

        confirmed = st.checkbox(
            "I understand this is a simulated paper order.",
            key="paper_order_confirmation",
        )

        if intent:
            st.info(
                f"Queued from Atlas: **{intent.get('ticker')}** · "
                f"{intent.get('reason') or 'Paper trade'}"
            )

        risk_blocked = (
            side == "BUY"
            and (
                risk_decision is None
                or not risk_decision.allowed
                or guardrail_status is None
                or not guardrail_status.allowed
            )
        )

        if st.button(
            f"Place Paper {side}",
            type="primary",
            width="stretch",
            disabled=(not confirmed) or risk_blocked,
            key="place_paper_order",
        ):
            order_service = PaperOrderService(
                db_path,
                commission=commission,
                slippage_pct=slippage_pct,
            )

            atlas_score = context.get("Atlas Score", context.get("Score"))

            try:
                if side == "BUY":
                    execution = order_service.buy_market(
                        ticker=ticker,
                        shares=shares,
                        market_price=market_price,
                        reason=reason,
                        notes=notes,
                        confidence=confidence,
                        atlas_score=atlas_score,
                    )
                else:
                    execution = order_service.sell_market(
                        ticker=ticker,
                        shares=shares,
                        market_price=market_price,
                        reason=reason,
                        notes=notes,
                        confidence=confidence,
                        atlas_score=atlas_score,
                    )
            except ValueError as error:
                st.error(str(error))
            else:
                clear_paper_trade_intent()
                st.success(
                    f"{execution.side} filled: {execution.shares:g} "
                    f"{execution.ticker} @ ${execution.filled_price:,.2f}"
                )
                st.rerun()


def display_order_history(
    *,
    db_path: str = "data/paper_trading.db",
) -> None:
    """Display filled order and completed trade history."""

    service = PaperOrderService(db_path)
    orders = service.list_orders()
    trades = service.list_trades()

    st.subheader("📋 Order History")

    if not orders:
        st.info("No paper orders have been placed.")
    else:
        order_df = pd.DataFrame(orders)
        visible = [
            "created_at",
            "ticker",
            "side",
            "requested_shares",
            "requested_price",
            "filled_price",
            "commission",
            "slippage",
            "status",
            "notes",
        ]
        st.dataframe(
            order_df[
                [
                    column
                    for column in visible
                    if column in order_df.columns
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    st.subheader("✅ Completed Trades")

    if not trades:
        st.info("No SELL orders have completed a trade yet.")
    else:
        trade_df = pd.DataFrame(trades)
        st.dataframe(
            trade_df,
            width="stretch",
            hide_index=True,
        )
