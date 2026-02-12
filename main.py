import re
import asyncio
from telethon import TelegramClient, events, Button
from telethon.errors import MessageIdInvalidError

# ================== بياناتك ==================
api_id = 34034006
api_hash = "3c072a85099d74436802a2ca6ca1df6b"
session_name = "session"

source_channel = -1003808609180   # آيدي القناة الخاصة
target_group = -1003573081848     # آيدي الجروب
image_after = "image.jpg"  # حط الصورة دي في نفس مجلد السكربت
# =============================================

client = TelegramClient(session_name, api_id, api_hash)

# كلمات يتم تجاهلها
IGNORE_WORDS = [
    "Verification Successful",
    "Access Denied",
    "@MissRose_bot",
    "You must join our channels"
]

# تخزين الرسائل الأصلية
stored_messages = {}


def extract_country(text):
    match = re.search(r'\b[A-Z]{2}\b', text)
    return match.group(0) if match else "Unknown"


@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    text = event.raw_text or ""

    # تجاهل الرسائل المحددة
    if any(word in text for word in IGNORE_WORDS):
        return

    # استخراج الدولة
    country = extract_country(text)

    # إرسال الرسالة للجروب
    sent = await client.send_message(target_group, text)

    # تخزين الرسالة
    stored_messages[sent.id] = text

    # انتظار دقيقة ونص
    await asyncio.sleep(90)

    try:
        await client.delete_messages(target_group, sent.id)
    except MessageIdInvalidError:
        return

    caption = f"""لقد تم تفعيل هذا الرقم من قبل شخص اخر✨❤️‍🩹
المطور @S_E_L2
Country: {country}"""

    # زر العرض مرة اخرى
    buttons = [
        [Button.inline("العرض مرة اخري", data=f"show_{sent.id}")]
    ]

    await client.send_file(
        target_group,
        image_after,
        caption=caption,
        buttons=buttons
    )


@client.on(events.CallbackQuery)
async def callback(event):
    data = event.data.decode()

    if data.startswith("show_"):
        msg_id = int(data.split("_")[1])

        if msg_id in stored_messages:
            await event.respond(
                stored_messages[msg_id]
            )
        else:
            await event.answer("الرسالة غير متاحة", alert=True)


print("Bot Running...")
client.start()
client.run_until_disconnected()
