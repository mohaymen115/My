# ========= SELVA ALL-IN-ONE CHAT =========
import os, json, secrets, datetime
from fastapi import FastAPI, Request, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from passlib.hash import bcrypt
import uvicorn

# ============ CONFIG ============
OWNER_NAME = "Selva"
OWNER_PASSWORD = "mohaymen"
OWNER_BADGE = "الــكــبــيــر"

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

engine = create_engine("sqlite:///selva.db", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI()
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
connections = {}

# ============ DATABASE ============
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    password = Column(String)
    badge = Column(String, default="")
    bio = Column(String, default="")
    avatar = Column(String, default="")
    is_owner = Column(Boolean, default=False)
    online = Column(Boolean, default=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender = Column(Integer)
    receiver = Column(Integer)
    content = Column(Text)
    type = Column(String)
    time = Column(String)

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    owner = Column(Integer)
    members = Column(Text)

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    owner = Column(Integer)

Base.metadata.create_all(engine)

# ============ INIT OWNER ============
db = Session()
if not db.query(User).filter_by(name=OWNER_NAME).first():
    db.add(User(
        name=OWNER_NAME,
        password=bcrypt.hash(OWNER_PASSWORD),
        badge=OWNER_BADGE,
        is_owner=True
    ))
    db.commit()
db.close()

# ============ LOGIN ============
@app.get("/", response_class=HTMLResponse)
def login_page():
    return """
<h2>Selva Chat</h2>
<form method="post" action="/login">
<input name="name" placeholder="Name"><br>
<input name="password" type="password" placeholder="Password"><br>
<button>Login / Register</button>
</form>
"""

@app.post("/login")
def login(name: str = Form(...), password: str = Form(...)):
    db = Session()
    user = db.query(User).filter_by(name=name).first()
    if user:
        if not bcrypt.verify(password, user.password):
            return "Wrong password"
    else:
        user = User(name=name, password=bcrypt.hash(password))
        db.add(user)
        db.commit()
    res = RedirectResponse("/chat", 302)
    res.set_cookie("uid", str(user.id))
    return res

# ============ CHAT UI ============
@app.get("/chat", response_class=HTMLResponse)
def chat(request: Request):
    uid = request.cookies.get("uid")
    if not uid:
        return RedirectResponse("/")
    db = Session()
    u = db.query(User).get(int(uid))
    return f"""
<h3>{u.name} {u.badge}</h3>
ID: {u.id}<br>
<textarea id=msg></textarea><br>
<input id=to placeholder="User ID">
<button onclick=send()>Send</button>
<pre id=box></pre>

<input type=file id=file>
<button onclick=upload()>Send File</button>

<script>
let ws=new WebSocket("ws://"+location.host+"/ws/{u.id}");
ws.onmessage=e=>box.textContent+=e.data+"\\n";

function send(){{
 ws.send(JSON.stringify({{to:to.value,msg:msg.value,type:"text"}}))
 msg.value=""
}}

function upload(){{
 let f=file.files[0]
 let fd=new FormData()
 fd.append("file",f)
 fetch("/upload",{method:"POST",body:fd})
 .then(r=>r.text()).then(p=>{{
 ws.send(JSON.stringify({{to:to.value,msg:p,type:"file"}}))
 }})
}}
</script>
"""

# ============ UPLOAD ============
@app.post("/upload")
async def upload(file: UploadFile):
    path = UPLOAD_DIR + "/" + secrets.token_hex(8) + "_" + file.filename
    with open(path, "wb") as f:
        f.write(await file.read())
    return path

# ============ WEBSOCKET ============
@app.websocket("/ws/{uid}")
async def ws(ws: WebSocket, uid: int):
    await ws.accept()
    connections[uid] = ws
    db = Session()
    db.query(User).get(uid).online = True
    db.commit()

    try:
        while True:
            data = await ws.receive_json()
            to = int(data["to"])
            msg = data["msg"]
            t = data["type"]
            db.add(Message(
                sender=uid,
                receiver=to,
                content=msg,
                type=t,
                time=str(datetime.datetime.now())
            ))
            db.commit()
            sender = db.query(User).get(uid).name
            if to in connections:
                await connections[to].send_text(f"{sender}: {msg}")
    except WebSocketDisconnect:
        connections.pop(uid)
        db.query(User).get(uid).online = False
        db.commit()

# ============ RUN ============
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
