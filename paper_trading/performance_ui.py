import math
import plotly.express as px
import streamlit as st
from .account import PaperAccountService
from .performance_analytics import (
    build_equity_history, calculate_performance_summary, daily_performance,
    monthly_performance, rolling_performance, trade_performance_breakdown,
    performance_trend, risk_adjusted_metrics, benchmark_comparison_from_history, fetch_benchmark_history,
)

def _ratio(v):
    if v is None: return "—"
    if math.isinf(v): return "∞"
    return f"{v:.2f}"

def display_performance_dashboard(db_path="data/paper_trading.db"):
    service=PaperAccountService(db_path)
    s=calculate_performance_summary(service)
    h=build_equity_history(service)
    st.subheader("📈 Performance Analytics")
    st.caption("Measure the paper-trading process, not a promise of future returns. Results become more useful as Atlas collects more completed trades and equity snapshots.")
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

    trend=performance_trend(service,10)
    st.markdown("#### Am I improving?")
    a,b,c,d=st.columns(4)
    a.metric("Recent Trend",trend["status"])
    b.metric("Recent Avg Return","—" if trend["recent_avg_return"] is None else f'{trend["recent_avg_return"]:.2%}')
    c.metric("Previous Avg Return","—" if trend["prior_avg_return"] is None else f'{trend["prior_avg_return"]:.2%}')
    d.metric("Change","—" if trend["return_delta"] is None else f'{trend["return_delta"]:+.2%}')
    if trend["status"]=="Insufficient evidence":
        st.info("Atlas needs at least two recent trades and two earlier trades before calling the performance trend improving, stable, or declining.")

    if h.empty:
        st.info("Performance history will appear after account snapshots are recorded.")
        return

    st.markdown("#### Account performance")
    st.plotly_chart(px.line(h,x="captured_at",y="equity",title="Paper Account Equity"),width="stretch")
    fig=px.line(h,x="captured_at",y="cumulative_return",title="Cumulative Return"); fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig,width="stretch")
    fig=px.area(h,x="captured_at",y="drawdown_pct",title="Account Drawdown"); fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig,width="stretch")

    risk=risk_adjusted_metrics(service)
    st.markdown("#### Risk-adjusted view")
    cols=st.columns(5)
    vals=[("Annualised Return",risk["annualised_return"],"pct"),("Annualised Volatility",risk["annualised_volatility"],"pct"),
          ("Sharpe",risk["sharpe"],"ratio"),("Sortino",risk["sortino"],"ratio"),("Calmar",risk["calmar"],"ratio")]
    for col,(label,val,kind) in zip(cols,vals):
        col.metric(label,"—" if val is None else (f"{val:.2%}" if kind=="pct" else f"{val:.2f}"))
    st.caption("Risk-adjusted statistics use recorded paper-account snapshots. Short histories can make annualised figures unstable, so treat early readings as descriptive evidence only.")

    st.markdown("#### Atlas paper account vs SPY")
    st.caption("A date-aligned comparison over the same recorded period. SPY is a benchmark reference, not a claim that either approach will outperform in future.")
    start_date=h["captured_at"].min().date()
    end_date=(h["captured_at"].max()+__import__("pandas").Timedelta(days=1)).date()
    spy=fetch_benchmark_history(start_date,end_date,"SPY")
    bench=benchmark_comparison_from_history(service,spy,"SPY",minimum_days=5)
    if bench["observations"] < 2:
        st.info("SPY comparison is unavailable until Atlas has overlapping paper-account and benchmark history.")
    else:
        bc=st.columns(5)
        bc[0].metric("Atlas Return",f'{bench["account_return"]:.2%}')
        bc[1].metric("SPY Return",f'{bench["benchmark_return"]:.2%}')
        bc[2].metric("Excess Return",f'{bench["excess_return"]:+.2%}')
        bc[3].metric("Atlas Max Drawdown",f'{bench["account_max_drawdown"]:.2%}')
        bc[4].metric("SPY Max Drawdown",f'{bench["benchmark_max_drawdown"]:.2%}')
        comp=bench["frame"][["date","account_return","benchmark_return"]].rename(columns={"account_return":"Atlas","benchmark_return":"SPY"}).melt("date",var_name="Series",value_name="Cumulative Return")
        fig=px.line(comp,x="date",y="Cumulative Return",color="Series",title="Atlas vs SPY — Same Period")
        fig.update_yaxes(tickformat=".1%")
        st.plotly_chart(fig,width="stretch")
        rc=st.columns(4)
        rc[0].metric("Atlas Volatility","—" if bench["account_volatility"] is None else f'{bench["account_volatility"]:.2%}')
        rc[1].metric("SPY Volatility","—" if bench["benchmark_volatility"] is None else f'{bench["benchmark_volatility"]:.2%}')
        rc[2].metric("Atlas Sharpe","—" if bench["account_sharpe"] is None else f'{bench["account_sharpe"]:.2f}')
        rc[3].metric("SPY Sharpe","—" if bench["benchmark_sharpe"] is None else f'{bench["benchmark_sharpe"]:.2f}')
        if bench["status"]=="Insufficient evidence":
            st.info(f'Only {bench["observations"]} overlapping observations are available. Treat the comparison as early descriptive evidence, not a conclusion.')

    st.markdown("#### What is making or losing money?")
    by_ticker=trade_performance_breakdown(service,"ticker")
    if by_ticker.empty:
        st.info("Complete paper trades to unlock ticker-level performance attribution.")
    else:
        st.dataframe(by_ticker,width="stretch",hide_index=True,column_config={"Win Rate":st.column_config.NumberColumn(format="%.1%%"),"Avg Return":st.column_config.NumberColumn(format="%.2%%"),"Best Return":st.column_config.NumberColumn(format="%.2%%"),"Worst Return":st.column_config.NumberColumn(format="%.2%%"),"Net P&L":st.column_config.NumberColumn(format="$%.2f")})

    c=st.columns(4)
    c[0].metric("Current Win Streak",s.current_win_streak); c[1].metric("Current Loss Streak",s.current_loss_streak)
    c[2].metric("Longest Win Streak",s.longest_win_streak); c[3].metric("Longest Loss Streak",s.longest_loss_streak)

    left,right=st.columns(2)
    with left:
        st.markdown("#### Daily Performance")
        dly=daily_performance(service)
        st.dataframe(dly[["captured_at","equity","daily_pnl","daily_return"]].tail(30),width="stretch",hide_index=True)
    with right:
        st.markdown("#### Monthly Performance")
        st.dataframe(monthly_performance(service),width="stretch",hide_index=True)

    window=st.slider("Rolling window",2,30,5,key="paper_perf_window")
    roll=rolling_performance(service,window)
    fig=px.line(roll,x="captured_at",y="rolling_return",title=f"{window}-Day Rolling Return"); fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig,width="stretch")
