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

# -------- تجاهل الرسائل --------
IGNORE_TEXTS = [
    "⚠️ Access Denied",
    "You must join our channels to use this bot",
    "Verification Successful",
    "Welcome! You now have full access to the bot",
]

IGNORE_BOTS = ["MissRose_bot"]

# ==== دالة تعديل النص العربي ====
def ar(text):
    return get_display(arabic_reshaper.reshape(text))

# ==== دالة تحويل النص لصورة ====
def text_to_image(text, filename="msg.png"):
    width, height = 900, 600

    # خلفية سوداء RGBA
    img = Image.new("RGBA", (width, height), (0, 0, 0, 255))

    try:
        font = ImageFont.truetype("arial.ttf", 70)
        small_font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    reshaped_text = ar(text)

    draw_dummy = ImageDraw.Draw(img)
    # لف النص لو طويل
    lines = []
    words = reshaped_text.split()
    line = ""
    for word in words:
        test = line + " " + word if line else word
        if draw_dummy.textlength(test, font=font) < width - 100:
            line = test
        else:
            lines.append(line)
            line = word
    lines.append(line)
    final_text = "\n".join(lines)

    bbox = draw_dummy.multiline_textbbox((0, 0), final_text, font=font, align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) / 2
    y = (height - text_height) / 2

    # ===== توهج نيون =====
    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.multiline_text(
        (x, y),
        final_text,
        font=font,
        fill=(0, 255, 255, 255),  # نيون سماوي
        align="center",
        spacing=10
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(15))
    img = Image.alpha_composite(img, glow_layer)

    # ===== النص الأبيض فوق التوهج =====
    final_draw = ImageDraw.Draw(img)
    final_draw.multiline_text(
        (x, y),
        final_text,
        font=font,
        fill="white",
        align="center",
        spacing=10
    )

    # اسم القناة أعلى
    final_draw.text(
        (width / 2, 40),
        channel_name,
        fill="cyan",
        font=small_font,
        anchor="mm"
    )

    # العلامة المائية أسفل
    final_draw.text(
        (width / 2, height - 40),
        watermark,
        fill="gray",
        font=small_font,
        anchor="mm"
    )

    img = img.convert("RGB")
    img.save(filename)
    return filename

# ==== التعامل مع الرسائل الجديدة ====
@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    if not event.raw_text:
        return

    text = event.raw_text

    # تجاهل رسائل محددة
    if any(word in text for word in IGNORE_TEXTS):
        return

    # تجاهل رسائل من بوتات معينة
    sender = await event.get_sender()
    if sender and sender.username in IGNORE_BOTS:
        return

    # إنشاء الصورة وإرسالها
    img = text_to_image(text)
    await client.send_file(target_group, img)
    os.remove(img)

print("Bot is running...")
client.start()
client.run_until_disconnected()
