def calculate_indicators(data, short_ma, long_ma):
    close = data["Close"].squeeze()

    ma_short = close.rolling(window=short_ma).mean()
    ma_long = close.rolling(window=long_ma).mean()

    latest_close = close.iloc[-1]
    latest_ma_short = ma_short.iloc[-1]
    latest_ma_long = ma_long.iloc[-1]

    strength = (
        (latest_ma_short - latest_ma_long)
        / latest_ma_long
    ) * 100

    return (
        close,
        ma_short,
        ma_long,
        latest_close,
        latest_ma_short,
        latest_ma_long,
        strength
    )


def generate_signal(latest_ma_short, latest_ma_long):
    if latest_ma_short > latest_ma_long:
        return "BUY"
    elif latest_ma_short < latest_ma_long:
        return "SELL"
    else:
        return "HOLD"