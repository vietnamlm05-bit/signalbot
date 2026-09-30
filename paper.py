"""Động cơ paper trading: chỉ long (spot), mọi lệnh bắt buộc có stop-loss."""
import json
from datetime import datetime, timezone
import db
from config import (SYMBOLS, START_EQUITY, FEE, SLIPPAGE, RISK_PER_TRADE, MIN_NOTIONAL,
                    ATR_SL, ATR_TP, CRITERIA)
from strategy import decide

HOUR_MS = 3_600_000

def fmt(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def equity(con):
    cash = db.get(con, "cash")
    for sym, qty in con.execute("SELECT symbol, qty FROM positions"):
        cash += qty * db.get(con, f"last_close:{sym}")
    return cash

def _close(con, sym, pos, ts, px, reason, notify):
    qty, entry, sl, tp, entry_ms = pos
    pnl = qty * px * (1 - FEE) - qty * entry * (1 + FEE)
    db.put(con, "cash", db.get(con, "cash") + qty * px * (1 - FEE))
    con.execute("INSERT INTO trades (symbol,entry_ms,exit_ms,entry,exit,qty,sl,tp,pnl,exit_reason)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)", (sym, entry_ms, ts, entry, px, qty, sl, tp, pnl, reason))
    con.execute("DELETE FROM positions WHERE symbol=?", (sym,))
    notify(f"🔴 ĐÓNG {sym} ({reason}) @ {px:,.2f} | PnL {pnl:+.2f} USDT | {fmt(ts)}")

def _open(con, sym, row, ts, notify):
    atr = float(row["atr"])
    entry = float(row["close"]) * (1 + SLIPPAGE)
    sl, tp = entry - ATR_SL * atr, entry + ATR_TP * atr
    if not (atr > 0 and 0 < sl < entry):
        return "stop-loss không hợp lệ"
    cash = db.get(con, "cash")
    n_open = con.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
    n_free = max(len(SYMBOLS) - n_open, 1)
    qty = equity(con) * RISK_PER_TRADE / (entry - sl)           # rủi ro 1% vốn
    qty = min(qty, cash / n_free / (entry * (1 + FEE)))          # không vượt tiền mặt
    if qty * entry < MIN_NOTIONAL:
        return "lệnh quá nhỏ"
    db.put(con, "cash", cash - qty * entry * (1 + FEE))
    con.execute("INSERT INTO positions VALUES (?,?,?,?,?,?)", (sym, qty, entry, sl, tp, ts))
    notify(f"🟢 MUA {sym} @ {entry:,.2f} | SL {sl:,.2f} | TP {tp:,.2f} | "
           f"qty {qty:.6f} | {fmt(ts)}")
    return None

def process(con, sym, row, news, notify):
    ts = int(row["ts"])
    pos = con.execute("SELECT qty,entry,sl,tp,entry_ms FROM positions WHERE symbol=?",
                      (sym,)).fetchone()
    if pos:  # kiểm tra SL/TP trong nến này (nếu chạm cả hai, giả định chạm SL trước)
        sl, tp = pos[2], pos[3]
        if row["low"] <= sl:
            _close(con, sym, pos, ts, min(sl, row["open"]) * (1 - SLIPPAGE), "stop-loss", notify)
            pos = None
        elif row["high"] >= tp:
            _close(con, sym, pos, ts, max(tp, row["open"]) * (1 - SLIPPAGE), "take-profit", notify)
            pos = None
    action, score, why = decide(row, news)
    if pos and action == "SELL":
        _close(con, sym, pos, ts, float(row["close"]) * (1 - SLIPPAGE), "tín hiệu SELL", notify)
    elif not pos and action == "BUY":
        skip = _open(con, sym, row, ts, notify)
        if skip:
            action = "HOLD"; why.append("bỏ BUY: " + skip)
    con.execute("INSERT INTO signals VALUES (?,?,?,?,?,?,?)",
                (ts, sym, float(row["close"]), score, news, action, json.dumps(why, ensure_ascii=False)))

def step(con, now_ms, frames, news, notify):
    """frames: symbol -> DataFrame nến ĐÃ ĐÓNG kèm chỉ báo."""
    if db.get(con, "start_ms") is None:   # lần chạy đầu: chỉ khởi tạo, không backfill quá khứ
        db.put(con, "start_ms", now_ms)
        db.put(con, "cash", START_EQUITY)
        db.put(con, "criteria", CRITERIA)
        for sym, df in frames.items():
            db.put(con, f"last_ts:{sym}", int(df["ts"].iloc[-1]))
            db.put(con, f"start_price:{sym}", float(df["close"].iloc[-1]))
            db.put(con, f"last_close:{sym}", float(df["close"].iloc[-1]))
        con.execute("INSERT INTO equity VALUES (?,?)", (now_ms, START_EQUITY))
        notify(f"▶️ SignalBot bắt đầu paper trading {', '.join(frames)} | vốn ảo {START_EQUITY} USDT")
        return
    events = []
    for sym, df in frames.items():
        new = df[df["ts"] > db.get(con, f"last_ts:{sym}")]
        events += [(int(r["ts"]), sym, r) for _, r in new.iterrows()]
    events.sort(key=lambda e: (e[0], e[1]))        # xử lý theo thời gian, bù cả nến bị lỡ
    for ts, sym, row in events:
        db.put(con, f"last_close:{sym}", float(row["close"]))
        process(con, sym, row, news.get(sym.split("/")[0], 0.0), notify)
        db.put(con, f"last_ts:{sym}", ts)
    con.execute("INSERT INTO equity VALUES (?,?)", (now_ms, equity(con)))
