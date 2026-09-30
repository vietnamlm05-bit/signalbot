"""Báo cáo + chấm tiêu chí. Chạy: python report.py"""
import time
import db
import notify
from config import BAR_MS, TIMEFRAME, SYMBOLS, START_EQUITY, CRITERIA
from paper import fmt

def build(con, now_ms=None):
    now_ms = now_ms or int(time.time() * 1000)
    start = db.get(con, "start_ms")
    if start is None:
        return "Chưa có dữ liệu: bot chưa chạy lần nào."
    crit = db.get(con, "criteria")
    bars = max(int((now_ms - start) // BAR_MS), 1)
    hours = (now_ms - start) / 3_600_000
    ok_bars = {ts // BAR_MS for (ts,) in con.execute(
        "SELECT ts FROM runs WHERE ok=1 AND ts>?", (start,))}
    uptime = min(len(ok_bars) / bars, 1.0)
    failed = con.execute("SELECT COUNT(*) FROM runs WHERE ok=0").fetchone()[0]

    trades = con.execute("SELECT pnl, sl, entry FROM trades").fetchall()
    opened = con.execute("SELECT sl, entry FROM positions").fetchall()
    n = len(trades)
    wins = sum(1 for p, _, _ in trades if p > 0)
    all_sl = [(sl, e) for _, sl, e in trades] + opened
    sl_cov = (sum(1 for sl, e in all_sl if sl is not None and 0 < sl < e) / len(all_sl)) if all_sl else 1.0

    eq = [v for (v,) in con.execute("SELECT value FROM equity ORDER BY ts")]
    ret = (eq[-1] / START_EQUITY - 1) * 100
    peak, mdd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = max(mdd, (peak - v) / peak * 100)
    bh = sum(db.get(con, f"last_close:{s}") / db.get(con, f"start_price:{s}") - 1
             for s in SYMBOLS) / len(SYMBOLS) * 100

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
