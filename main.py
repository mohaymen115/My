import os
import threading
from telethon import TelegramClient, events
import telebot
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# ========= بياناتك =========
api_id = 34034006
api_hash = "3c072a85099d74436802a2ca6ca1df6b"
session_name = "session"

source_channel = -1003808609180   # آيدي قناتك الخاصة
bot_token = "8388224467:AAHtsoKJuWHA3aSVve-gFigtCqXQEANMru0"
group_id = -1003573081848        # آيدي الجروب

channel_name = "My Private Channel"
watermark = "@YourUsername"
# ===========================

client = TelegramClient(session_name, api_id, api_hash)
bot = telebot.TeleBot(bot_token)

def ar(text):
    return get_display(arabic_reshaper.reshape(text))

def text_to_image(text, filename="msg.png"):
    img = Image.new("RGB", (900, 600), "black")
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

# لما توصله صورة من Telethon يبعتها للجروب
@bot.message_handler(content_types=['photo'])
def forward_to_group(message):
    bot.send_photo(group_id, message.photo[-1].file_id)

def run_bot():
    print("Bot running...")
    bot.infinity_polling()

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    if not event.raw_text:
        return

    img = text_to_image(event.raw_text)
    await client.send_file(f"@{bot.get_me().username}", img)
    os.remove(img)

def run_telethon():
    print("Telethon running...")
    client.start()
    client.run_until_disconnected()

# تشغيل الاثنين مع بعض
threading.Thread(target=run_bot).start()
run_telethon()
