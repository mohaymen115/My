import os
import random
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
ignore_bot = "MissRose_bot"
# ===========================

client = TelegramClient(session_name, api_id, api_hash)

ignored_texts = [
    "⚠️ Access Denied",
    "You must join our channels to use this bot.",
    "Verification Successful!",
    "Welcome! You now have full access to the bot."
]

def ar(text):
    return get_display(arabic_reshaper.reshape(text))

def should_ignore(event):
    if event.sender and getattr(event.sender, "username", "") == ignore_bot:
        return True
    if any(x in event.raw_text for x in ignored_texts):
        return True
    return False

def draw_lightning(draw, start_x, start_y, end_x, end_y):
    points = [(start_x, start_y)]
    segments = 8
    for i in range(1, segments):
        x = start_x + (end_x - start_x) * i / segments + random.randint(-20, 20)
        y = start_y + (end_y - start_y) * i / segments + random.randint(-20, 20)
        points.append((x, y))
    points.append((end_x, end_y))
    draw.line(points, fill=(0, 200, 255), width=3)

def create_lightning_neon(text, output="lightning.gif"):
    base = Image.open("background.jpg").resize((900, 600)).convert("RGBA")
    frames = []

    try:
        font = ImageFont.truetype("arial.ttf", 85)
        small_font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    text = ar(text)

    for glow in range(100, 255, 30):

        frame = base.copy()

        overlay = Image.new("RGBA", frame.size, (0, 0, 0, 150))
        frame = Image.alpha_composite(frame, overlay)

        txt_layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_layer)

        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        x = (900 - w) / 2
        y = (600 - h) / 2

        # توهج نيون
        for i in range(8):
            draw.text((x, y), text, font=font, fill=(0, glow, 255))
        draw.text((x, y), text, font=font, fill="white")

        # برق حوالين النص
        draw_lightning(draw, x-50, y-20, x+w+50, y-20)
        draw_lightning(draw, x-50, y+h+20, x+w+50, y+h+20)

        txt_layer = txt_layer.filter(ImageFilter.GaussianBlur(4))
        frame = Image.alpha_composite(frame, txt_layer)

        draw_final = ImageDraw.Draw(frame)
        draw_final.text((30, 30), channel_name, fill="cyan", font=small_font)
        draw_final.text((650, 560), watermark, fill="gray", font=small_font)

        frames.append(frame.convert("RGB"))

    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=70,
        loop=0
    )

    return output

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    if not event.raw_text:
        return

    if should_ignore(event):
        return

    gif = create_lightning_neon(event.raw_text)
    await client.send_file(target_group, gif)
    os.remove(gif)

print("⚡ Lightning Neon Bot Running ⚡")
client.start()
client.run_until_disconnected()
