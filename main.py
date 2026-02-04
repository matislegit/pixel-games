from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
import uvicorn
import os

app = FastAPI()
BASE_DIR = Path(__file__).parent

# -------------------------------
# Developer password from environment variable
# -------------------------------
DEV_PASSWORD = os.getenv("DEV_PASSWORD", "changeme")  # Default fallback

DATA_FILE = BASE_DIR / "document.json"

# Load or initialize document
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
# WebSocket
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
# Run server
# -------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
