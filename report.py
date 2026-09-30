"""Báo cáo + chấm tiêu chí. Chạy: python report.py"""
import time
import db
import notify
from config import BAR_MS, TIMEFRAME, SYMBOLS, START_EQUITY, CRITERIA
from paper import fmt

PERIODS = {"1d": 1, "3d": 3, "7d": 7, "1w": 7, "2w": 14, "1m": 30, "3m": 90, "6m": 180}
DAY_MS = 86_400_000

def build(con, now_ms=None, period=None):
    """period=None: báo cáo đầy đủ + chấm tiêu chí. period='3d'...: hiệu suất trong khoảng đó."""
    now_ms = now_ms or int(time.time() * 1000)
    start = db.get(con, "start_ms")
    if start is None:
        return "Chưa có dữ liệu: bot chưa chạy lần nào."
    since, note = start, ""
    if period:
        want = now_ms - PERIODS[period] * DAY_MS
        since = max(want, start)
        if want < start:
            note = f"(bot mới chạy {(now_ms - start) / DAY_MS:.1f} ngày, chưa đủ {period})"
    crit = db.get(con, "criteria")
    bars = max(int((now_ms - since) // BAR_MS), 1)
    hours = (now_ms - since) / 3_600_000
    ok_bars = {ts // BAR_MS for (ts,) in con.execute(
        "SELECT ts FROM runs WHERE ok=1 AND ts>?", (since,))}
    uptime = min(len(ok_bars) / bars, 1.0)
    failed = con.execute("SELECT COUNT(*) FROM runs WHERE ok=0 AND ts>?", (since,)).fetchone()[0]

    trades = con.execute("SELECT pnl, sl, entry FROM trades WHERE exit_ms>=?", (since,)).fetchall()
    opened = con.execute("SELECT sl, entry FROM positions").fetchall()
    n = len(trades)
    wins = sum(1 for p, _, _ in trades if p > 0)
    pnl = sum(p for p, _, _ in trades)
    all_sl = [(sl, e) for _, sl, e in trades] + opened
    sl_cov = (sum(1 for sl, e in all_sl if sl is not None and 0 < sl < e) / len(all_sl)) if all_sl else 1.0

    row = con.execute("SELECT value FROM equity WHERE ts<=? ORDER BY ts DESC LIMIT 1", (since,)).fetchone()
    base = row[0] if row else START_EQUITY
    eq = [base] + [v for (v,) in con.execute("SELECT value FROM equity WHERE ts>? ORDER BY ts", (since,))]
    ret = (eq[-1] / base - 1) * 100
    peak, mdd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = max(mdd, (peak - v) / peak * 100)
    bh_parts = []
    for s in SYMBOLS:
        p0 = con.execute("SELECT price FROM signals WHERE symbol=? AND ts>=? ORDER BY ts LIMIT 1",
                         (s, since)).fetchone()
        p0 = p0[0] if p0 else db.get(con, f"start_price:{s}")
        bh_parts.append(db.get(con, f"last_close:{s}") / p0 - 1)
    bh = sum(bh_parts) / len(bh_parts) * 100

    if period:
        lines = [
            f"📊 Báo cáo {period} {note}".strip(),
            f"Từ {fmt(since)} đến {fmt(now_ms)} ({hours:.1f} giờ)",
            "",
            f"- Vốn ảo: {base:.2f} → {eq[-1]:.2f} USDT ({ret:+.2f}%)",
            f"- Mua-và-giữ cùng kỳ: {bh:+.2f}%",
            f"- Lệnh đã đóng: {n} | thắng: {wins} ({(wins / n if n else 0):.0%}) | PnL: {pnl:+.2f} USDT",
            f"- Đang mở: {len(opened)} | Max drawdown: {mdd:.2f}%",
            f"- Uptime: {uptime:.1%} | lần chạy lỗi: {failed}",
        ]
        return "\n".join(lines)

    checks = [
        ("Uptime", f"{uptime:.1%}", f">= {crit['min_uptime']:.0%}", uptime >= crit["min_uptime"]),
        ("Lệnh có stop-loss", f"{sl_cov:.0%}", f">= {crit['sl_coverage']:.0%}", sl_cov >= crit["sl_coverage"]),
        ("So với mua-và-giữ", f"{ret - bh:+.2f} điểm %", f">= -{crit['max_underperf_pct']}",
         ret - bh >= -crit["max_underperf_pct"]),
        ("Max drawdown", f"{mdd:.2f}%", f"<= {crit['max_drawdown_pct']}%", mdd <= crit["max_drawdown_pct"]),
        ("Số lệnh đã đóng", str(n), f">= {crit['min_trades']}", n >= crit["min_trades"]),
    ]
    lines = [
        "# Báo cáo SignalBot (paper trading)",
        f"Từ {fmt(start)} đến {fmt(now_ms)} ({hours:.1f} giờ, {bars} nến {TIMEFRAME})",
        "",
        f"- Vốn ảo: {START_EQUITY:.2f} → {eq[-1]:.2f} USDT ({ret:+.2f}%)",
        f"- Mua-và-giữ cùng kỳ: {bh:+.2f}%",
        f"- Lệnh đã đóng: {n} | thắng: {wins} ({(wins / n if n else 0):.0%}) | đang mở: {len(opened)}",
        f"- Lần chạy lỗi: {failed}",
        "",
        "| Tiêu chí | Kết quả | Ngưỡng | Đạt |",
        "|---|---|---|---|",
    ]
    lines += [f"| {a} | {b} | {c} | {'✅' if d else '❌'} |" for a, b, c, d in checks]
    passed = all(c[3] for c in checks)
    lines += ["", "**Kết luận:** " + ("Đạt tất cả tiêu chí, có thể XEM XÉT bước 6 (vốn nhỏ, tự bấm lệnh)."
              if passed else "Chưa đạt, CHƯA sang bước 6. Tiếp tục paper trade hoặc sửa chiến lược.")]
    if crit != CRITERIA:
        lines.append("\n⚠️ config.py đã đổi tiêu chí sau khi bắt đầu. Báo cáo dùng tiêu chí gốc.")
    return "\n".join(lines)

if __name__ == "__main__":
    text = build(db.connect())
    print(text)
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(text + "\n")
    notify.send(text.replace("**", ""))
