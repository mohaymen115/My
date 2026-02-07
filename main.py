import requests
import time
import json
import os

# ================== CONFIG ==================
BOT_TOKEN = "8584758167:AAG1m7fJNsMhzYh00q1v4DNyy000L406ASI"

SITE_URL = "https://kobrapanel-production.up.railway.app"
LOGIN_URL = SITE_URL + "/login"
API_URL = SITE_URL + "/api"
SITE_PASSWORD = "selva1"

CHECK_INTERVAL = 5  # ثواني
DATA_FILE = "users.json"

PANEL_LINK = "https://panel-production-15f6.up.railway.app/"

# ================== STORAGE ==================
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================== TELEGRAM API ==================
def tg(method, payload=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    r = requests.post(url, json=payload, timeout=20)
    return r.json()

def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    tg("sendMessage", payload)

# ================== SITE SESSION ==================
session = requests.Session()

def site_login():
    r = session.post(
        LOGIN_URL,
        data={"password": SITE_PASSWORD},
        allow_redirects=True,
        timeout=20
    )
    if r.status_code not in (200, 302):
        raise Exception("❌ Site login failed")

# ================== BOT LOGIC ==================
users = load_users()
sent_messages = set()
offset = 0

def main_menu():
    return {
        "inline_keyboard": [
            [{"text": "➕ إضافة OTP", "callback_data": "add_otp"}]
        ]
    }

def handle_updates():
    global offset, users

    r = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
        params={"offset": offset, "timeout": 30},
        timeout=40
    )

    data = r.json()
    if not data.get("ok"):
        return

    for update in data["result"]:
        offset = update["update_id"] + 1

        # ===== Messages =====
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")
            user_id = str(msg["from"]["id"])

            if text == "/start":
                send_message(
                    chat_id,
                    "👋 أهلاً بك في SELVA PANEL OTP\n\nاضغط الزر لإضافة جروب استقبال OTP",
                    main_menu()
                )

            elif users.get(user_id, {}).get("waiting_group"):
                try:
                    group_id = int(text.strip())
                    users[user_id] = {
                        "group_id": group_id,
                        "waiting_group": False
                    }
                    save_users(users)

                    send_message(
                        chat_id,
                        "✅ تم حفظ ID الجروب\n\nسيتم إرسال OTP تلقائيًا"
                    )
                except:
                    send_message(chat_id, "❌ ابعت ID الجروب رقم فقط")

        # ===== Buttons =====
        if "callback_query" in update:
            cq = update["callback_query"]
            user_id = str(cq["from"]["id"])
            chat_id = cq["message"]["chat"]["id"]
            data_cb = cq["data"]

            if data_cb == "add_otp":
                users[user_id] = {
                    "waiting_group": True
                }
                save_users(users)

                send_message(
                    chat_id,
                    "📥 ابعت الآن ID الجروب\n\nمثال:\n-1001234567890"
                )

# ================== OTP SENDER ==================
def send_otps():
    r = session.get(API_URL, timeout=20)
    if r.status_code != 200:
        return

    messages = r.json()

    for m in messages:
        text = m.get("text")
        if not text:
            continue

        if text in sent_messages:
            continue

        for info in users.values():
            group_id = info.get("group_id")
            if group_id:
                send_message(
                    group_id,
                    f"""SELVA PANEL OTP ⚡

{text}

Panel:
{PANEL_LINK}
"""
                )

        sent_messages.add(text)

        if len(sent_messages) > 1000:
            sent_messages.clear()

# ================== RUN ==================
def run():
    site_login()
    print("✅ SELVA PANEL OTP Bot Started")

    while True:
        try:
            handle_updates()
            send_otps()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print("⚠️ Error:", e)
            time.sleep(5)

if __name__ == "__main__":
    run()
