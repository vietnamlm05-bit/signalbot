import math
from config import BUY_SCORE, SELL_SCORE, NEWS_BLOCK

def decide(row, news):
    """Trả về (action, score, reasons). Luật rõ ràng, dễ backtest."""
    vals = [row["ema20"], row["ema50"], row["rsi"], row["macd_hist"], row["atr"]]
    if any(v is None or math.isnan(v) for v in vals):
        return "HOLD", 0, ["thiếu dữ liệu chỉ báo"]
    s, why = 0, []
    if row["ema20"] > row["ema50"]:
        s += 1; why.append("EMA20>EMA50")
    else:
        s -= 1; why.append("EMA20<EMA50")
    if row["macd_hist"] > 0:
        s += 1; why.append("MACD hist>0")
    else:
        s -= 1; why.append("MACD hist<0")
    if row["rsi"] < 30:
        s += 1; why.append(f"RSI {row['rsi']:.0f} quá bán")
    elif row["rsi"] > 70:
        s -= 1; why.append(f"RSI {row['rsi']:.0f} quá mua")
    if news >= 0.3:
        s += 1; why.append(f"tin tích cực {news:+.2f}")
    elif news <= -0.3:
        s -= 1; why.append(f"tin tiêu cực {news:+.2f}")
    if s >= BUY_SCORE and news > NEWS_BLOCK:
        return "BUY", s, why
    if s <= SELL_SCORE:
        return "SELL", s, why
    return "HOLD", s, why
