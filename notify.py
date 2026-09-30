import json
import os
import requests

def _cfg():
    return os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")

def _call(method, **kw):
    tok, _ = _cfg()
    r = requests.post(f"https://api.telegram.org/bot{tok}/{method}", timeout=20, json=kw)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"{method}: {data.get('error_code')} {data.get('description')}")
    return data["result"]

def send(text, reply_markup=None):
    """Gửi tin. Lỗi Telegram hiện thành annotation đỏ (::error::) trong log GitHub Actions."""
    tok, chat = _cfg()
    if not tok or not chat:
        print("[telegram tắt]", text)
        return False
    try:
        kw = {"chat_id": chat, "text": text[:4000]}
        if reply_markup:
            kw["reply_markup"] = reply_markup
        _call("sendMessage", **kw)
        return True
    except Exception as ex:
        print(f"::error::Telegram lỗi: {ex}")
        return False

def get_updates(offset):
    return _call("getUpdates", offset=offset, timeout=0,
                 allowed_updates=["message", "callback_query"])

def answer_callback(cb_id):
    try:
        _call("answerCallbackQuery", callback_query_id=cb_id)
    except Exception as ex:
        print("answerCallbackQuery lỗi:", ex)
