import pandas as pd


def moving_average(series, period):
    return series.rolling(period).mean()


def calculate_rsi(close, period=14):
    delta = close.diff()

    gain = delta.where(delta > 0, 0)

    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()

    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_indicators(data, short_ma, long_ma):

    close = data["Close"].squeeze()

    ma_short = moving_average(close, short_ma)

    ma_long = moving_average(close, long_ma)

    rsi = calculate_rsi(close)

    latest_close = close.iloc[-1]

    latest_ma_short = ma_short.iloc[-1]

    latest_ma_long = ma_long.iloc[-1]

    latest_rsi = rsi.iloc[-1]

    strength = (
        (latest_ma_short - latest_ma_long)
        / latest_ma_long
    ) * 100

    return (
        close,
        ma_short,
        ma_long,
        rsi,
        latest_close,
        latest_ma_short,
        latest_ma_long,
        latest_rsi,
        strength,
    )


def generate_signal(ma_short, ma_long):

    if ma_short > ma_long:
        return "BUY"

    elif ma_short < ma_long:
        return "SELL"

    return "HOLD"