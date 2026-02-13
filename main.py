import asyncio
import logging
import hashlib
from datetime import datetime
import requests

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

DELETE_AFTER_SECONDS = 300
EDIT_AFTER_SECONDS = 90

# ============================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()

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
                },
                timeout=15
            )
            if r.status_code == 200:
                self.token = r.json().get("token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                logger.info("Logged in to panel successfully")
                return True
            else:
                logger.error(f"Login failed: {r.status_code}")
        except Exception as e:
            logger.error(f"Login exception: {e}")
        return False

    def fetch_messages(self):
        try:
            r = self.session.get(f"{PANEL_URL}/api/sms?limit=50", timeout=15)
            if r.status_code == 200:
                try:
                    data = r.json()
                    if isinstance(data, list):
                        return data
                except ValueError:
                    logger.error("Invalid JSON from panel")
        except Exception as e:
            logger.error(f"Fetch messages exception: {e}")
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
    except Exception:
        pass

# ============================================
# EDIT MESSAGE WITH VIDEO
# ============================================

async def edit_message_with_video(chat_id, message_id):
    await asyncio.sleep(EDIT_AFTER_SECONDS)

    try:
        # delete original OTP message
        await bot.delete_message(chat_id=chat_id, message_id=message_id)

        # send video
        sent_video = await bot.send_video(
            chat_id=chat_id,
            video=VIDEO_URL,
            caption=(
                "تم تفعيل هذا الرقم من قبل شخص اخر✨❤️‍🩹\n"
                "قناه الارقام ✨❤️‍🩹\n"
                "https://t.me/selva_num"
            )
        )

        # schedule deletion
        asyncio.create_task(
            delete_message_later(chat_id, sent_video.message_id, DELETE_AFTER_SECONDS)
        )

    except Exception as e:
        logger.error(f"Edit message exception: {e}")

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

# ============================================
# BACKGROUND MONITOR
# ============================================

async def background_monitor():
    while True:
        try:
            messages = scraper.fetch_messages()

            for msg in messages:
                if isinstance(msg, dict) and otp_filter.is_new(msg):
                    text = (
                        "<b>✦ NEW OTP ✦</b>\n\n"
                        f"📱 {msg.get('number','Unknown')}\n"
                        f"💬 {msg.get('content','')}"
                    )
                    await async_send_otp(text)

            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Background monitor exception: {e}")
            await asyncio.sleep(10)

# ============================================
# MAIN
# ============================================

async def main():
    # start background monitor as task
    asyncio.create_task(background_monitor())
    # run bot polling
    await application.run_polling()

if __name__ == "__main__":
    print("BOT STARTED")
    asyncio.run(main())
