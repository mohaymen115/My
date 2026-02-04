import asyncio
from flask import Flask, request, jsonify, render_template_string
from telethon import TelegramClient, events
from telegram import Bot

# ================= CONFIG =================
API_ID = 39864754
API_HASH = "254da5354e8595342d963ef27049c"
SESSION_NAME = "ko"

CHANNEL_ID = -1003808609180
# =========================================

BOT_TOKEN = None
GROUP_ID = None
logs = []

app = Flask(__name__)

# ================= DARK THEME SITE =================
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Selva ⚡</title>
<style>
*{box-sizing:border-box}
body{
margin:0;
height:100vh;
background:
linear-gradient(rgba(0,0,0,.85),rgba(0,0,0,.85)),
url("https://i.ibb.co/m1jd1Hx/bg.jpg") center/cover no-repeat;
font-family:Segoe UI,Arial;
color:#fff;
display:flex;
justify-content:center;
align-items:center;
}
.panel{
width:420px;
background:#0e0e0e;
border-radius:16px;
padding:25px;
box-shadow:0 0 40px #000;
}
h1{
margin:0 0 15px;
text-align:center;
letter-spacing:1px;
}
input{
width:100%;
padding:12px;
margin:8px 0;
border-radius:8px;
border:none;
outline:none;
background:#1b1b1b;
color:#fff;
}
button{
width:100%;
padding:12px;
margin-top:10px;
border:none;
border-radius:8px;
background:linear-gradient(135deg,#7f00ff,#e100ff);
color:#fff;
font-weight:bold;
cursor:pointer;
}
button:hover{opacity:.9}
.log{
margin-top:15px;
background:#111;
border-radius:10px;
padding:10px;
max-height:260px;
overflow:auto;
font-size:14px;
}
.msg{
padding:6px;
border-bottom:1px solid #222;
color:#ddd;
}
</style>
</head>
<body>

<div class="panel">
<h1>Selva ⚡</h1>

<input id="token" placeholder="Bot Token">
<input id="group" placeholder="Group ID">

<button onclick="connect()">Create OTP Bot</button>

<div class="log" id="log"></div>
</div>

<script>
function connect(){
fetch("/connect",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
bot_token:document.getElementById("token").value,
group_id:document.getElementById("group").value
})
}).then(r=>r.json()).then(()=>{
alert("Connected");
});
}

setInterval(()=>{
fetch("/messages")
.then(r=>r.json())
.then(data=>{
let log=document.getElementById("log");
log.innerHTML="";
data.slice().reverse().forEach(m=>{
log.innerHTML += `<div class="msg">${m}</div>`;
});
});
},1500);
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/connect", methods=["POST"])
def connect():
    global BOT_TOKEN, GROUP_ID
    data = request.json
    BOT_TOKEN = data["bot_token"]
    GROUP_ID = int(data["group_id"])
    return jsonify({"status": "ok"})

@app.route("/messages")
def messages():
    return jsonify(logs)

# ================= TELETHON =================
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def send_everywhere(text):
    if BOT_TOKEN and GROUP_ID:
        bot = Bot(BOT_TOKEN)
        await bot.send_message(chat_id=GROUP_ID, text=text)

    logs.append(text)
    if len(logs) > 150:
        logs.pop(0)

@client.on(events.NewMessage(chats=CHANNEL_ID))
async def handler(event):
    if event.text:
        await send_everywhere(event.text)

async def start_telethon():
    await client.start()
    print("Telethon running...")
    await client.run_until_disconnected()

# ================= RUN =================
def main():
    loop = asyncio.get_event_loop()
    loop.create_task(start_telethon())
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()

