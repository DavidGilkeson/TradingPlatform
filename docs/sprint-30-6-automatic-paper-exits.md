# Project Atlas — Sprint 30.6 Automatic Paper Exits

Sprint 30.6 adds optional automatic simulated exits.

## Behaviour

When enabled and manually checked, Atlas:

- reads saved stop-loss and take-profit plans
- compares them with current paper-position prices
- simulates a full SELL when a level is triggered
- records STOP_LOSS or TAKE_PROFIT as the exit reason
- updates cash and realised P&L
- writes the SELL into order history and journal
- removes the completed exit plan

The feature is intentionally opt-in.

Trigger checks currently run only when the user presses "Check Exit Triggers
Now". No live brokerage orders are sent.
