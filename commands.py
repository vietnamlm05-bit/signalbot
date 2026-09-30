"""Nhận lệnh Telegram (getUpdates) mỗi lần chạy: /report, /report 3d, hoặc bấm nút."""
import db
import notify
import report
import os

ORDER = ["1d", "3d", "7d", "2w", "1m", "3m", "6m"]
KEYBOARD = {"inline_keyboard": [
    [{"text": p, "callback_data": f"report:{p}"} for p in ORDER[:4]],
    [{"text": p, "callback_data": f"report:{p}"} for p in ORDER[4:]] + [
        {"text": "toàn bộ", "callback_data": "report:all"}],
]}

def _run(con, arg):
    try:
        _run_inner(con, arg)
    except Exception as ex:
        print(f"::error::Lỗi xử lý /report: {ex!r}")
        notify.send(f"⚠️ Không tạo được báo cáo: {ex!r}")

def _run_inner(con, arg):
    if arg == "all":
        notify.send(report.build(con).replace("**", ""))
    elif arg in report.PERIODS:
        notify.send(report.build(con, period=arg))
    else:
        notify.send("Chọn khung báo cáo:", reply_markup=KEYBOARD)

def handle(con):
    """Đọc lệnh mới, trả lời. Chỉ nghe chat của chủ bot."""
    chat = str(os.getenv("TELEGRAM_CHAT_ID", ""))
    offset = int(db.get(con, "tg_offset", 0))
    try:
        updates = notify.get_updates(offset)
    except Exception as ex:
        print(f"::error::Không đọc được lệnh Telegram: {ex}")
        return
    for u in updates:
        offset = max(offset, u["update_id"] + 1)
        cb = u.get("callback_query")
        if cb:
            if str(cb["message"]["chat"]["id"]) == chat:
                notify.answer_callback(cb["id"])
                data = cb.get("data", "")
                if data.startswith("report:"):
                    _run(con, data.split(":", 1)[1])
            continue
        m = u.get("message") or {}
        if str(m.get("chat", {}).get("id")) != chat:
            continue
        parts = (m.get("text") or "").strip().lower().split()
        if parts and parts[0].split("@")[0] == "/report":
            _run(con, parts[1] if len(parts) > 1 else "")
    db.put(con, "tg_offset", offset)
    con.commit()
