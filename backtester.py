import yfinance as yf

from config import PERIOD, SHORT_MA, LONG_MA
from indicators import calculate_indicators


def backtest(ticker):

    print(f"\nBacktesting {ticker}...")

    data = yf.download(
        ticker,
        period="5y",
        progress=False
    )

    (
        close,
        ma_short,
        ma_long,
        rsi,
        latest_close,
        latest_ma_short,
        latest_ma_long,
        latest_rsi,
        latest_volume,
        average_volume,
        strength,
    ) = calculate_indicators(
        data,
        SHORT_MA,
        LONG_MA,
    )

    cash = 10000
    shares = 0

    for i in range(1, len(close)):

        if (
            ma_short.iloc[i] > ma_long.iloc[i]
            and
            ma_short.iloc[i - 1] <= ma_long.iloc[i - 1]
            and
            shares == 0
        ):

            shares = cash / close.iloc[i]
            cash = 0

        elif (
            ma_short.iloc[i] < ma_long.iloc[i]
            and
            ma_short.iloc[i - 1] >= ma_long.iloc[i - 1]
            and
            shares > 0
        ):

            cash = shares * close.iloc[i]
            shares = 0

    if shares > 0:
        cash = shares * close.iloc[-1]

    print(f"Final Portfolio Value: ${cash:,.2f}")

    return cash