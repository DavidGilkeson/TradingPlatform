def calculate_score(signal, strength, rsi, volume, average_volume):

    score = 0
    reasons = []

    # Moving Average Signal
    if signal == "BUY":
        score += 40
        reasons.append("Bullish moving averages")

    # Trend Strength
    if strength > 10:
        score += 25
        reasons.append("Strong trend")
    elif strength > 5:
        score += 15

    # RSI
    if 40 <= rsi <= 60:
        score += 20
        reasons.append("Healthy RSI")

    elif 30 <= rsi < 40:
        score += 15

    # Volume
    if volume > average_volume:
        score += 15
        reasons.append("Above average volume")

    return score, reasons

def confidence_rating(score):
    
    if score >= 90:
        return "★★★★★ Strong Buy"

    elif score >= 80:
        return "★★★★☆ Buy"

    elif score >= 70:
        return "★★★☆☆ Watch"

    elif score >= 60:
        return "★★☆☆☆ Weak"

    else:
        return "★☆☆☆☆ Avoid"