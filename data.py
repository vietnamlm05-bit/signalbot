"""Lấy nến OHLCV công khai qua ccxt (không cần API key)."""
import pandas as pd
from config import EXCHANGE, TIMEFRAME

_ex = None

def fetch_ohlcv(symbol, limit=200):
    global _ex
    import ccxt
    if _ex is None:
        _ex = getattr(ccxt, EXCHANGE)({"enableRateLimit": True})
    rows = _ex.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=limit)
    return pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
