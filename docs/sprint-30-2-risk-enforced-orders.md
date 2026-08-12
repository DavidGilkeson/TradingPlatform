# Project Atlas — Sprint 30.2 Risk-Enforced Order Ticket

Sprint 30.2 connects the Risk Manager directly to the Paper BUY ticket.

Before a simulated BUY can be placed, Atlas checks account equity, available
paper cash, stop-loss distance, maximum risk per trade, maximum position
exposure, target price, and reward/risk.

The BUY button is disabled when a hard risk rule is broken.

Atlas also calculates a suggested position size and lets the user apply it
directly to the paper order ticket. SELL orders remain available for position
management.
