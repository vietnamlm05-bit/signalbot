"""Mô phỏng 7 ngày bằng dữ liệu GIẢ (không cần mạng) để kiểm tra logic.
Chạy: python tests/test_sim.py   (từ thư mục gốc dự án)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import db, main, report
from config import SYMBOLS, START_EQUITY, FEE
from config import BAR_MS

rng = np.random.default_rng(42)
T0 = 1_780_000_000_000 // BAR_MS * BAR_MS
N = 2400

def make_candles(price):
    rets = rng.normal(0, 0.008, N) + np.repeat(rng.normal(0, 0.002, N // 50 + 1), 50)[:N]
    close = price * np.exp(np.cumsum(rets))
    open_ = np.r_[price, close[:-1]]
    spread = np.abs(rng.normal(0, 0.004, N)) * close
    return pd.DataFrame({"ts": T0 + np.arange(N) * BAR_MS, "open": open_,
                         "high": np.maximum(open_, close) + spread,
                         "low": np.minimum(open_, close) - spread,
                         "close": close, "volume": 1.0})

DATA = {"BTC/USDT": make_candles(60000), "ETH/USDT": make_candles(3000)}
clock = {"now": 0}

def fake_fetch(sym):   # trả cả nến đang chạy để kiểm tra việc lọc nến chưa đóng
    df = DATA[sym]
    return df[df["ts"] <= clock["now"]].tail(200).reset_index(drop=True)

def fake_news(symbols):
    return {"BTC": float(rng.uniform(-0.6, 0.6)), "ETH": float(rng.uniform(-0.6, 0.6))}

msgs = []
if os.path.exists("sim.db"):
    os.remove("sim.db")
con = db.connect("sim.db")
start = T0 + 250 * BAR_MS + 2 * 60_000
skip_hours = {480, 481, 482}     # giả lập GitHub Actions bỏ lỡ 3 lần chạy
fail_hour = 1200                 # giả lập 1 lần lỗi mạng

for h in range(0, 7 * 24 * 12 + 1):
    clock["now"] = start + h * BAR_MS
    if h in skip_hours:
        continue
    if h == fail_hour:
        try:
            main.run(clock["now"], lambda s: (_ for _ in ()).throw(ConnectionError("mất mạng")),
                     fake_news, con, msgs.append)
        except ConnectionError:
            pass
        continue
    main.run(clock["now"], fake_fetch, fake_news, con, msgs.append)

# ---- Kiểm tra tính đúng ----
start_ms = db.get(con, "start_ms")
for sym in SYMBOLS:
    df = DATA[sym]
    expected = df[(df["ts"] > df[df["ts"] + BAR_MS <= start]["ts"].max()) &
                  (df["ts"] + BAR_MS <= clock["now"])]
    got = con.execute("SELECT ts FROM signals WHERE symbol=? ORDER BY ts", (sym,)).fetchall()
    assert [g[0] for g in got] == list(expected["ts"]), f"{sym}: nến bị lặp hoặc bị bỏ"

realized = sum(p for (p,) in con.execute("SELECT pnl FROM trades"))
unreal = sum(q * db.get(con, f"last_close:{s}") - q * e * (1 + FEE)
             for s, q, e in con.execute("SELECT symbol, qty, entry FROM positions"))
final_eq = con.execute("SELECT value FROM equity ORDER BY ts DESC LIMIT 1").fetchone()[0]
assert abs(START_EQUITY + realized + unreal - final_eq) < 1e-6, "sổ sách tiền không khớp"
assert db.get(con, "cash") >= -1e-9, "tiền mặt âm"
bad = con.execute("SELECT COUNT(*) FROM trades WHERE sl IS NULL OR sl<=0 OR sl>=entry").fetchone()[0]
assert bad == 0, "có lệnh thiếu stop-loss"
assert con.execute("SELECT COUNT(*) FROM runs WHERE ok=0").fetchone()[0] == 1

for per in ("1d", "3d", "1w", "2w", "1m", "6m"):
    txt = report.build(con, clock["now"], period=per)
    assert "Vốn ảo" in txt, per
print(report.build(con, clock["now"], period="3d"), "\n")
print(report.build(con, clock["now"]))
print("\nTin nhắn Telegram (5 cái đầu):")
for m in msgs[:5]:
    print(" ", m)
print(f"\nTổng tin nhắn: {len(msgs)}")
print("\n✅ TẤT CẢ KIỂM TRA LOGIC ĐỀU ĐẠT")
con.close()
os.remove("sim.db")
