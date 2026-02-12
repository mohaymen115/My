import os
from telethon import TelegramClient, events
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# ========= بياناتك =========
api_id = 34034006
api_hash = "3c072a85099d74436802a2ca6ca1df6b"
session_name = "session"

source_channel = -1003808609180   # آيدي القناة الخاصة
target_group = -1003573081848     # آيدي الجروب

channel_name = "My Private Channel"
watermark = "@YourUsername"
# ===========================

client = TelegramClient(session_name, api_id, api_hash)

def ar(text):
    return get_display(arabic_reshaper.reshape(text))

def text_to_image(text, filename="msg.png"):
    width, height = 900, 600
    img = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 42)
        small_font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    draw.multiline_text((40, 120), ar(text), fill="white", font=font, align="right")
    draw.text((40, 40), channel_name, fill="cyan", font=small_font)
    draw.text((600, 550), watermark, fill="gray", font=small_font)

    img.save(filename)
    return filename

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    if not event.raw_text:
        return

    img = text_to_image(event.raw_text)
    await client.send_file(target_group, img)
    os.remove(img)

print("Bot is running on Railway...")
client.start()
client.run_until_disconnected()
