import math
import plotly.express as px
import streamlit as st
from .account import PaperAccountService
from .performance_analytics import build_equity_history, calculate_performance_summary, daily_performance, monthly_performance, rolling_performance

def _ratio(v):
    if v is None: return "—"
    if math.isinf(v): return "∞"
    return f"{v:.2f}"

def display_performance_dashboard(db_path="data/paper_trading.db"):
    service=PaperAccountService(db_path)
    s=calculate_performance_summary(service)
    h=build_equity_history(service)
    st.subheader("📈 Performance Dashboard")
    r1=st.columns(6)
    vals=[("Equity",f"${s.current_equity:,.2f}"),("Net Profit",f"${s.net_profit:,.2f}"),
          ("Total Return",f"{s.total_return:.2%}"),("Win Rate",f"{s.win_rate:.1%}"),
          ("Profit Factor",_ratio(s.profit_factor)),("Max Drawdown",f"{s.max_drawdown:.2%}")]
    for c,(l,v) in zip(r1,vals): c.metric(l,v)
    r2=st.columns(6)
    vals=[("Realised P&L",f"${s.realised_pnl:,.2f}"),("Unrealised P&L",f"${s.unrealised_pnl:,.2f}"),
          ("Expectancy",f"${s.expectancy:,.2f}"),("Avg Trade",f"{s.average_trade_return:.2%}"),
          ("Best Trade",f"{s.best_trade_return:.2%}"),("Worst Trade",f"{s.worst_trade_return:.2%}")]
    for c,(l,v) in zip(r2,vals): c.metric(l,v)

    if h.empty:
        st.info("Performance history will appear after account snapshots are recorded.")
        return

    st.plotly_chart(px.line(h,x="captured_at",y="equity",title="Paper Account Equity"),width="stretch")
    fig=px.line(h,x="captured_at",y="cumulative_return",title="Cumulative Return"); fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig,width="stretch")
    fig=px.area(h,x="captured_at",y="drawdown_pct",title="Account Drawdown"); fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig,width="stretch")

    c=st.columns(4)
    c[0].metric("Current Win Streak",s.current_win_streak)
    c[1].metric("Current Loss Streak",s.current_loss_streak)
    c[2].metric("Longest Win Streak",s.longest_win_streak)
    c[3].metric("Longest Loss Streak",s.longest_loss_streak)

    left,right=st.columns(2)
    with left:
        st.markdown("#### Daily Performance")
        d=daily_performance(service)
        st.dataframe(d[["captured_at","equity","daily_pnl","daily_return"]].tail(30),width="stretch",hide_index=True)
    with right:
        st.markdown("#### Monthly Performance")
        m=monthly_performance(service)
        st.dataframe(m,width="stretch",hide_index=True)

    window=st.slider("Rolling window",2,30,5,key="paper_perf_window")
    roll=rolling_performance(service,window)
    fig=px.line(roll,x="captured_at",y="rolling_return",title=f"{window}-Day Rolling Return"); fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig,width="stretch")
