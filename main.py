from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
import uvicorn
import os

app = FastAPI()

# ---------------------------
# BASE DIRECTORY
# ---------------------------
BASE_DIR = Path(__file__).parent

DATA_FILE = BASE_DIR / "document.json"
INDEX_FILE = BASE_DIR / "index.html"

# Change this in production
DEV_PASSWORD = os.getenv("DEV_PASSWORD", "changeme")

# ---------------------------
# LOAD / INIT DATA
# ---------------------------
if DATA_FILE.exists():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {"content": ""}
else:
    data = {"content": ""}

def save_to_file():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------------------------
# ROUTES
# ---------------------------

@app.get("/", response_class=HTMLResponse)
async def home():
    if INDEX_FILE.exists():
        return INDEX_FILE.read_text(encoding="utf-8")
    return "<h1>index.html not found</h1>"

@app.get("/load")
async def load_doc():
    return {"content": data["content"]}

# ---------------------------
# WEBSOCKET HANDLER
# ---------------------------

clients = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)

    # Send current document on connect
    await websocket.send_json({
        "content": data["content"]
    })

    try:
        while True:
            msg = await websocket.receive_json()

            password = msg.get("password", "")
            content = msg.get("content", "")

            # Only dev can update
            if password == DEV_PASSWORD:

                data["content"] = content
                save_to_file()

                # Broadcast to all clients
                dead_clients = set()

                for client in clients:
                    try:
                        await client.send_json({
                            "content": content
                        })
                    except:
                        dead_clients.add(client)

                # Remove disconnected clients
                for dc in dead_clients:
                    clients.discard(dc)

    except WebSocketDisconnect:
        clients.discard(websocket)

    except Exception as e:
        print("WebSocket error:", e)
        clients.discard(websocket)

# ---------------------------
# MAIN
# ---------------------------

if __name__ == "__main__":

    # Render provides PORT env var
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
