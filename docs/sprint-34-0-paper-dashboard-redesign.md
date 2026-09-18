# Sprint 34.0 — Paper Trading Dashboard Redesign

Sprint 34.0 turns the top of Atlas Paper Trading into a compact command centre.
It is a presentation/UX sprint: order execution, risk enforcement and intelligence
logic are unchanged.

## Command Centre

The dashboard now leads with six facts: equity, cash, invested value, total P&L,
total return and open positions. A smaller activity panel shows today's completed
trades and realised P&L, plus the cash/invested split.

The existing eight-stage trade lifecycle remains visible, but is paired with a
plain-English **Next action** so the user knows where to go next without needing
to understand Atlas's internal modules.

Detailed Trade, Portfolio, Forward Test, Intelligence, History and Account tools
remain available in their existing tabs. The command-centre helper is pure Python
and regression tested independently of Streamlit.
