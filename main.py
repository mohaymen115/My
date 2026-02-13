import asyncio
import logging
import hashlib
from datetime import datetime
import requests
from telegram import Bot
from telegram.ext import Application

# ================= CONFIG =================
BOT_TOKEN = "7783212048:AAFBym2E2Ro6yCiNKtc0eo-XyTc8_Qet_XQ"
GROUP_ID = -1003522997115

PANEL_URL = "http://198.135.52.238"
PANEL_USERNAME = "selva"
PANEL_PASSWORD = "selva123456"

VIDEO_URL = "https://drive.google.com/uc?export=download&id=1OGS3-mnoM7Q6P-MTl3GDrtU2_9BvL3Mr"
DELETE_AFTER_SECONDS = 300
EDIT_AFTER_SECONDS = 90
# =========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()

# ================= PANEL API =================
class PanelAPI:
    def __init__(self):
        self.session = requests.Session()
        self.token = None

    def login(self):
        try:
            r = self.session.post(
                f"{PANEL_URL}/api/auth/login",
                json={"username": PANEL_USERNAME, "password": PANEL_PASSWORD},
                timeout=15
            )
            if r.status_code == 200:
                self.token = r.json().get("token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                logger.info("Logged in to panel successfully")
                return True
        except Exception as e:
            logger.error(e)
        return False

    def fetch_messages(self):
        try:
            r = self.session.get(f"{PANEL_URL}/api/sms?limit=50", timeout=15)
            if r.status_code == 200:
                data = r.json()
                return data.get("messages", [])
        except Exception as e:
            logger.error(e)
        return []

scraper = PanelAPI()
scraper.login()

# ================= OTP FILTER =================
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

# ================= DELETE MESSAGE =================
async def delete_message_later(chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# ================= EDIT MESSAGE TO VIDEO =================
async def edit_message_with_video(chat_id, message_id):
    await asyncio.sleep(EDIT_AFTER_SECONDS)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        sent_video = await bot.send_video(
            chat_id=chat_id,
            video=VIDEO_URL,
            caption="تم تفعيل هذا الرقم من قبل شخص اخر✨❤️‍🩹\nقناه الارقام ✨❤️‍🩹\nhttps://t.me/selva_num"
        )
        asyncio.create_task(delete_message_later(chat_id, sent_video.message_id, DELETE_AFTER_SECONDS))
    except Exception as e:
        logger.error(e)

# ================= SEND OTP =================
async def async_send_otp(message):
    sent_msg = await bot.send_message(chat_id=GROUP_ID, text=message, parse_mode="HTML")
    asyncio.create_task(edit_message_with_video(GROUP_ID, sent_msg.message_id))
    asyncio.create_task(delete_message_later(GROUP_ID, sent_msg.message_id, DELETE_AFTER_SECONDS))

# ================= BACKGROUND MONITOR =================
async def background_monitor():
    while True:
        try:
            messages = scraper.fetch_messages()
            for msg in messages:
                if otp_filter.is_new(msg):
                    text = (
                        f"<b>✦ NEW OTP ✦</b>\n\n"
                        f"📱 {msg.get('phone_number','Unknown')}\n"
                        f"💬 {msg.get('message','')}\n"
                        f"OTP: {msg.get('otp','')}\n"
                        f"🌍 {msg.get('country','')}"
                    )
                    await async_send_otp(text)
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(e)
            await asyncio.sleep(10)

# ================= MAIN =================
if __name__ == "__main__":
    print("BOT STARTED")
    loop = asyncio.get_event_loop()
    loop.create_task(background_monitor())
    loop.create_task(application.run_polling())
    loop.run_forever()
