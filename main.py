import os
import asyncio
import logging
import requests
import hashlib
import threading
import time
from datetime import datetime
from telegram import Bot
from telegram.ext import Application

# ============================================
# CONFIG
# ============================================

BOT_TOKEN = "7783212048:AAFBym2E2Ro6yCiNKtc0eo-XyTc8_Qet_XQ"
GROUP_ID = -1003522997115  # حط ايدي الجروب هنا

PANEL_URL = "http://198.135.52.238"
PANEL_USERNAME = "selva"
PANEL_PASSWORD = "selva123456"

VIDEO_URL = "https://drive.google.com/uc?export=download&id=1OGS3-mnoM7Q6P-MTl3GDrtU2_9BvL3Mr"

DELETE_AFTER_SECONDS = 300  # 5 دقائق
EDIT_AFTER_SECONDS = 90     # دقيقة ونص

# ============================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()

bot_loop = None

# ============================================
# PANEL API
# ============================================

class PanelAPI:
    def __init__(self):
        self.session = requests.Session()
        self.token = None

    def login(self):
        try:
            r = self.session.post(
                f"{PANEL_URL}/api/auth/login",
                json={
                    "username": PANEL_USERNAME,
                    "password": PANEL_PASSWORD
                }
            )
            if r.status_code == 200:
                self.token = r.json()["token"]
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                return True
        except:
            pass
        return False

    def fetch_messages(self):
        try:
            r = self.session.get(f"{PANEL_URL}/api/sms?limit=50")
            if r.status_code == 200:
                return r.json()
        except:
            pass
        return []

scraper = PanelAPI()
scraper.login()

# ============================================
# OTP FILTER
# ============================================

class OTPFilter:
    def __init__(self):
        self.cache = {}

    def is_new(self, msg):
        h = hashlib.md5(str(msg).encode()).hexdigest()
        if h in self.cache:
            return False
        self.cache[h] = datetime.now()
        return True

otp_filter = OTPFilter()

# ============================================
# DELETE MESSAGE
# ============================================

async def delete_message_later(chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# ============================================
# CONVERT TO VIDEO AFTER 90s
# ============================================

async def edit_message_with_video(chat_id, message_id):
    await asyncio.sleep(EDIT_AFTER_SECONDS)

    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)

        sent_video = await bot.send_video(
            chat_id=chat_id,
            video=VIDEO_URL,
            caption=(
                "تم تفعيل هذا الرقم من قبل شخص اخر✨❤️‍🩹\n"
                "قناه الارقام ✨❤️‍🩹\n"
                "https://t.me/selva_num"
            )
        )

        asyncio.create_task(
            delete_message_later(chat_id, sent_video.message_id, DELETE_AFTER_SECONDS)
        )

    except Exception as e:
        logger.error(e)

# ============================================
# SEND OTP
# ============================================

async def async_send_otp(message):
    sent_msg = await bot.send_message(
        chat_id=GROUP_ID,
        text=message,
        parse_mode="HTML"
    )

    asyncio.create_task(
        edit_message_with_video(GROUP_ID, sent_msg.message_id)
    )

    asyncio.create_task(
        delete_message_later(GROUP_ID, sent_msg.message_id, DELETE_AFTER_SECONDS)
    )

def send_otp(message):
    asyncio.run_coroutine_threadsafe(async_send_otp(message), bot_loop)

# ============================================
# BACKGROUND MONITOR
# ============================================

def background_monitor():
    while True:
        try:
            messages = scraper.fetch_messages()

            for msg in messages:
                if otp_filter.is_new(msg):

                    text = (
                        "<b>✦ NEW OTP ✦</b>\n\n"
                        f"📱 {msg.get('number','Unknown')}\n"
                        f"💬 {msg.get('content','')}"
                    )

                    send_otp(text)

            time.sleep(30)

        except Exception as e:
            logger.error(e)
            time.sleep(10)

# ============================================
# START BOT
# ============================================

async def start_bot():
    global bot_loop
    bot_loop = asyncio.get_event_loop()

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    while True:
        await asyncio.sleep(1)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

# ============================================
# MAIN
# ============================================

threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=background_monitor, daemon=True).start()

print("BOT STARTED")

while True:
    time.sleep(1)
