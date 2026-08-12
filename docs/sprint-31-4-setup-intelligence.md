# Project Atlas — Sprint 31.4 Setup Intelligence

Atlas now analyses combinations of trade characteristics rather than only
isolated factors.

Available setup dimensions:

- Atlas Score band
- confidence band
- trend regime
- volatility regime
- verdict / trade reason

For each combination Atlas calculates:

- completed trades
- wins and win rate
- average return
- net P&L
- expectancy
- sample grade
- evidence level
- reliability score
- Insight Ready status

Atlas only promotes an evidence-qualified setup leader when the combination
passes the selected minimum evidence threshold.

This is important because adding dimensions can create tiny groups that appear
excellent by chance. Setup Intelligence therefore retains the sample-quality
safeguards introduced in Sprint 31.2.
