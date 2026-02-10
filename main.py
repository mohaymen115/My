import re
import os
import time
import asyncio
import requests
from telethon import TelegramClient, events
import telebot
from PIL import Image, ImageDraw, ImageFont

# ================== الإعدادات ==================

api_id = 30828166
api_hash = "272132c1323a4bb1fd6994d8d51977cf"
session_name = "user_session"

SOURCE_CHANNEL = "-1003808609180"
BLOCKED_BOT = "MissRose_bot"

BOT_TOKEN = "8577422070:AAEebTCfknIitxuV9CTXNcnSrFc0Wsa1PQE"
TARGET_GROUP_ID = -1003719096308   # جروبك

DEFAULT_IMAGE = "https://ibb.co/LDC7DLXx"

FLAG_IMAGES = {
    "58": ["https://ibb.co/ynhV5h38"],
    "263":["https://ibb.co/Y7kr6P0M"],
    "7":["https://ibb.co/BVx65srq"],
    "992": ["https://ibb.co/67xVFFxy"],
    "212": ["https://ibb.co/G3rksrLt"],
    "213": ["https://ibb.co/0VB916kG"],
    "966": ["https://ibb.co/YFjVYswB"],
    "971": ["https://ibb.co/FLLJDcQG"],
    "90": ["https://ibb.co/jPrDVRz7"],
    "49": ["https://ibb.co/Y7D9BjDW"],
    "33": ["https://ibb.co/x8rcJf1X"],
    "44": ["https://ibb.co/p6TgSxPM"],
    "39": ["https://ibb.co/kg2qH4T9"],
    "34": ["https://ibb.co/QvVPKGJ5"],
    "7": ["https://ibb.co/HTbnDqmS"]
}

# =================================================

bot = telebot.TeleBot(BOT_TOKEN)
client = TelegramClient(session_name, api_id, api_hash)

os.makedirs("temp", exist_ok=True)


def extract_country_code(text):
    match = re.search(r"\b(\d{1,3})\s*\d+", text)
    if match:
        return match.group(1)
    return None


def download_image(url, path):
    r = requests.get(url)
    with open(path, "wb") as f:
        f.write(r.content)


def write_text_on_image(image_path, text, output_path):
    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    w, h = img.size
    text_box = draw.multiline_textbbox((0, 0), text, font=font)
    tw = text_box[2] - text_box[0]
    th = text_box[3] - text_box[1]

    x = (w - tw) // 2
    y = h - th - 40

    draw.rectangle((x-10, y-10, x+tw+10, y+th+10), fill=(0, 0, 0, 180))
    draw.multiline_text((x, y), text, font=font, fill="white", align="center")

    img.save(output_path)


async def delete_after(chat_id, message_id, delay=300):
    await asyncio.sleep(delay)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_bot_message(message):
    text = message.text
    code = extract_country_code(text)

    if code and code in FLAG_IMAGES:
        img_url = FLAG_IMAGES[code][0]
    else:
        img_url = DEFAULT_IMAGE

    base_path = f"temp/base_{int(time.time())}.jpg"
    out_path = f"temp/out_{int(time.time())}.png"

    download_image(img_url, base_path)
    write_text_on_image(base_path, text, out_path)

    sent = bot.send_photo(TARGET_GROUP_ID, open(out_path, "rb"))
    asyncio.run_coroutine_threadsafe(delete_after(TARGET_GROUP_ID, sent.message_id), loop)

    os.remove(base_path)
    os.remove(out_path)


@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handler(event):
    sender = await event.get_sender()
    text = event.raw_text or ""

    if sender and sender.username:
        if sender.username.lower() == BLOCKED_BOT.lower():
            return

    blocked_phrases = [
        "Verification Successful",
        "Welcome! You now have full access",
        "Access Denied",
        "You must join our channels",
        "Please join the following channel",
        "After joining, click the button below to verify"
    ]

    for phrase in blocked_phrases:
        if phrase.lower() in text.lower():
            return

    bot.send_message(bot.get_me().id, text)


async def main():
    await client.start()
    print("✅ Userbot running...")
    await client.run_until_disconnected()


loop = asyncio.get_event_loop()
loop.create_task(main())
bot.infinity_polling()
