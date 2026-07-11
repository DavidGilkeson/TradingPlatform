def calculate_score(signal, strength, rsi):

    score = 0

    if signal == "BUY":
        score += 40

    if strength > 10:
        score += 30
    elif strength > 5:
        score += 20
    elif strength > 2:
        score += 10

    # Healthy RSI
    if 40 <= rsi <= 60:
        score += 20

    # Slightly oversold
    elif 30 <= rsi < 40:
        score += 15

    # Slightly overbought
    elif 60 < rsi <= 70:
        score += 10

    return score