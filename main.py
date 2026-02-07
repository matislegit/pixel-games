from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
import os
import uvicorn

app = FastAPI()
BASE_DIR = Path(__file__).parent

# -------------------------------
# Environment-based dev password
# -------------------------------
DEV_PASSWORD = os.getenv("DEV_PASSWORD", "")  # Set this in Render env

# -------------------------------
# Document storage
# -------------------------------
DATA_FILE = BASE_DIR / "document.json"

if DATA_FILE.exists():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {"content": ""}

def save_to_file():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

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
# Developer auth endpoint
# -------------------------------
@app.post("/auth")
async def auth(data: dict = Body(...)):
    password = data.get("password", "")
    if not DEV_PASSWORD:
        return {"ok": False, "error": "No server password set"}
    if password == DEV_PASSWORD:
        return {"ok": True}
    return {"ok": False}

# -------------------------------
# WebSocket setup
# -------------------------------
clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        # Send current document to new client
        await websocket.send_json({"content": data["content"]})
        while True:
            msg = await websocket.receive_json()
            password = msg.get("password", "")
            content = msg.get("content", "")
            # Only dev can send updates
            if password == DEV_PASSWORD:
                data["content"] = content
                save_to_file()
                # Broadcast updates to all other clients
                for client in clients:
                    if client != websocket:
                        await client.send_json({"content": content})
    except WebSocketDisconnect:
        clients.remove(websocket)

# -------------------------------
# Run server (for local dev)
# -------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
