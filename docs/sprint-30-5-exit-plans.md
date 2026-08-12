# Project Atlas — Sprint 30.5 Stop-Loss & Take-Profit Tracking

Sprint 30.5 adds persistent exit planning for open paper positions.

## Features

- saved stop-loss per open position
- saved take-profit target
- reward/risk calculation
- distance to stop
- distance to target
- stop-hit warning
- target-hit notification
- all-position exit-plan table

This sprint monitors exit levels only. It deliberately does not auto-close a
paper position when a stop or target is touched.

The next sprint can add optional automatic simulated exits with clear controls,
audit history, and tests.
