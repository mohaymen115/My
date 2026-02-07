import re
import os
import asyncio
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from telethon import TelegramClient, events

# ================== TELEGRAM CONFIG ==================
API_ID = 38077264
API_HASH = "4dac72033d68a6bab7586e67edb182ae"
SESSION_NAME = "selva_session"
SOURCE_CHANNEL = "TGW_Otp_Station"  # ضع اسم القناة هنا

# ================== FILTER ==================
REQUIRED_SERVICE = "💬 Service: Telegram"
NUMBER_REGEX = re.compile(r"📞\s*Number:\s*(\d+)")
ALLOWED_CODES = ("254", "994", "996", "216", "263")

# ================== STORAGE ==================
MAX_MESSAGES = 2  # نعرض آخر رسالتين فقط
messages_cache = []

# ================== APP ==================
app = FastAPI()
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ================== HELPERS ==================
def extract_number(text: str):
    m = NUMBER_REGEX.search(text)
    return m.group(1) if m else None

def is_allowed(number: str):
    return any(number.startswith(code) for code in ALLOWED_CODES)

# ================== TELETHON ==================
@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handler(event):
    text = event.message.message
    if not text:
        return

    # فلترة حسب الخدمة المطلوبة
    if REQUIRED_SERVICE not in text:
        return

    number = extract_number(text)
    if not number or not is_allowed(number):
        return

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted = f"[{timestamp}]\n{text}\n{'='*50}\n"

    messages_cache.append(formatted)
    if len(messages_cache) > MAX_MESSAGES:
        messages_cache.pop(0)  # نحافظ على آخر رسالتين فقط

    print("✅ Message added:", number)

# ================== FASTAPI ==================
@app.get("/", response_class=HTMLResponse)
async def home():
    content = "".join(messages_cache)

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>KobraPanel OTP</title>
<style>
body {{
    background:#0b0b0b;
    color:#00ff99;
    font-family: monospace;
    padding:20px;
}}
h2 {{
    text-align:center;
}}
pre {{
    background:#000;
    padding:20px;
    border-radius:10px;
    white-space:pre-wrap;
    max-height: 80vh;
    overflow-y: auto;
    font-size: 18px;
}}
button {{
    background:#00ff99;
    color:#000;
    padding:12px 20px;
    border:none;
    cursor:pointer;
    font-weight:bold;
    font-size:16px;
    margin-bottom:15px;
}}
</style>
<script>
setInterval(() => location.reload(), 4000);
</script>
</head>
<body>

<h2>📡 KOBRA OTP LIVE (Last 2)</h2>

<div style="text-align:center;">
<button onclick="navigator.clipboard.writeText(document.getElementById('data').innerText)">
📋 COPY ALL
</button>
</div>

<pre id="data">{content}</pre>

</body>
</html>
"""

# ================== STARTUP ==================
@app.on_event("startup")
async def startup():
    await client.start()
    asyncio.create_task(client.run_until_disconnected())
    print("🚀 Telethon connected & site live")

# ================== RUN ==================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
