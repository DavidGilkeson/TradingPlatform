# Project Atlas — Sprint 30.3 Portfolio Guardrails

Portfolio-wide risk controls now sit above individual trade risk checks.

## Guardrails

- maximum total portfolio exposure
- maximum number of open positions
- daily realised-loss limit
- consecutive-loss pause
- warning zone before exposure limits
- clear Trading Allowed / Trading Paused status

The guardrails pause new simulated BUY entries conceptually while preserving
SELL access for reducing or closing existing positions.

Sprint 30.4 can enforce these portfolio-wide rules directly in the order ticket
and add projected-exposure checks before a new BUY is submitted.
