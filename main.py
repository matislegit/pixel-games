from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
import os
import uvicorn

# -------------------------------
# App Setup
# -------------------------------
app = FastAPI()
BASE_DIR = Path(__file__).parent

# -------------------------------
# Environment Password
# -------------------------------
DEV_PASSWORD = os.getenv("DEV_PASSWORD", "")

# -------------------------------
# Document Storage
# -------------------------------
DATA_FILE = BASE_DIR / "document.json"


def load_document():
    """Load document from disk"""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"content": ""}
    return {"content": ""}


def save_document(content: str):
    """Save document to disk safely"""
    data = {"content": content}

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())  # Force disk write


# Load on boot
data = load_document()

# -------------------------------
# Routes
# -------------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    return (BASE_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/load")
async def load_doc():
    return {"content": data["content"]}


# -------------------------------
# Auth Endpoint
# -------------------------------
@app.post("/auth")
async def auth(data_body: dict = Body(...)):
    password = data_body.get("password", "")

    if not DEV_PASSWORD:
        return {"ok": False, "error": "Server password not set"}

    if password == DEV_PASSWORD:
        return {"ok": True}

    return {"ok": False}


# -------------------------------
# WebSocket
# -------------------------------
clients = []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)

    try:
        # Send current doc on connect
        await websocket.send_json({"content": data["content"]})

        while True:
            msg = await websocket.receive_json()

            password = msg.get("password", "")
            content = msg.get("content", "")

            # Only allow dev edits
            if password == DEV_PASSWORD:

                # Update memory
                data["content"] = content

                # Save to disk
                save_document(content)

                # Broadcast
                for client in clients:
                    if client != websocket:
                        await client.send_json({"content": content})

    except WebSocketDisconnect:
        if websocket in clients:
            clients.remove(websocket)


# -------------------------------
# Run (Local)
# -------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
