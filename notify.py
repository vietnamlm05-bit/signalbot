import os
import requests

def send(text):
    tok, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print("[telegram tắt]", text)
        return
    try:
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", timeout=20,
                      json={"chat_id": chat, "text": text[:4000]})
    except Exception as ex:
        print("Telegram lỗi:", ex)
