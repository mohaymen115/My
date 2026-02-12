import os
from telethon import TelegramClient, events
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# ========= بياناتك =========
api_id = 34034006
api_hash = "3c072a85099d74436802a2ca6ca1df6b"
session_name = "session"

source_channel = -1003808609180   # آيدي القناة الخاصة
target_group = -1003573081848     # آيدي الجروب

channel_name = "OTP Selva"
watermark = "@S_E_L2"
# ===========================

client = TelegramClient(session_name, api_id, api_hash)

# ----------- تجاهل الرسائل -----------
IGNORE_TEXTS = [
    "⚠️ Access Denied",
    "You must join our channels to use this bot.",
    "Verification Successful",
    "Welcome! You now have full access to the bot."
]

IGNORE_BOTS = ["MissRose_bot"]

def ar(text):
    return get_display(arabic_reshaper.reshape(text))

# ----------- تأثير نيون -----------
def draw_neon_text(draw, position, text, font):
    x, y = position

    # طبقة توهج
    for blur in range(8, 0, -2):
        glow = Image.new("RGB", (900, 600), "black")
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.text((x, y), text, font=font, fill=(0,255,255))
        glow = glow.filter(ImageFilter.GaussianBlur(blur))
        draw.bitmap((0,0), glow)

    # النص الأساسي
    draw.text((x, y), text, font=font, fill="white")

def text_to_image(text, filename="msg.png"):
    width, height = 900, 600
    img = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 70)   # خط أكبر
        small_font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    reshaped_text = ar(text)

    # حساب مكان النص في المنتصف
    bbox = draw.multiline_textbbox((0,0), reshaped_text, font=font, align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) / 2
    y = (height - text_height) / 2

    draw_neon_text(draw, (x, y), reshaped_text, font)

    # اسم القناة فوق
    draw.text((width/2, 40), channel_name, fill="cyan", font=small_font, anchor="mm")

    # العلامة المائية تحت
    draw.text((width/2, height-40), watermark, fill="gray", font=small_font, anchor="mm")

    img.save(filename)
    return filename


@client.on(events.NewMessage(chats=source_channel))
async def handler(event):

    # تجاهل لو مفيش نص
    if not event.raw_text:
        return

    # تجاهل رسائل من بوت معين
    sender = await event.get_sender()
    if sender and sender.username in IGNORE_BOTS:
        return

    # تجاهل رسائل معينة
    for word in IGNORE_TEXTS:
        if word in event.raw_text:
            return

    img = text_to_image(event.raw_text)
    await client.send_file(target_group, img)
    os.remove(img)

print("Bot is running...")
client.start()
client.run_until_disconnected()
