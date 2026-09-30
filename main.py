"""Chạy 1 lần (GitHub Actions gọi mỗi 5 phút)."""
import time
import db
import notify
import paper
from config import BAR_MS, SYMBOLS
from indicators import add_indicators

def run(now_ms=None, fetch=None, news_fn=None, con=None, send=None):
    now_ms = now_ms or int(time.time() * 1000)
    if fetch is None:
        from data import fetch_ohlcv as fetch
    if news_fn is None:
        from news import news_scores as news_fn
    send = send or notify.send
    con = con or db.connect()
    try:
        frames = {}
        for sym in SYMBOLS:
            df = fetch(sym)
            df = df[df["ts"] + BAR_MS <= now_ms]        # bỏ nến chưa đóng
            if len(df) < 60:
                raise RuntimeError(f"{sym}: thiếu dữ liệu ({len(df)} nến)")
            frames[sym] = add_indicators(df)
        news = news_fn(SYMBOLS)
        paper.step(con, now_ms, frames, news, send)
        con.execute("INSERT INTO runs VALUES (?,?,?)", (now_ms, 1, None))
        con.commit()
    except Exception as ex:
        con.rollback()
        con.execute("INSERT INTO runs VALUES (?,?,?)", (now_ms, 0, repr(ex)[:500]))
        con.commit()
        send(f"⚠️ SignalBot lỗi: {ex!r}")
        raise

if __name__ == "__main__":
    run()
