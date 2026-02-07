import os
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import uvicorn


# -------------------------------
# APP SETUP
# -------------------------------

app = FastAPI()
BASE_DIR = Path(__file__).parent


# -------------------------------
# SECURITY
# -------------------------------

# Set this in Render dashboard
DEV_PASSWORD = os.getenv("DEV_PASSWORD", "changeme123")

if DEV_PASSWORD == "changeme123":
    print("⚠️ WARNING: DEV_PASSWORD not set in environment!")


# -------------------------------
# DATA STORAGE
# -------------------------------

DATA_FILE = BASE_DIR / "document.json"

if DATA_FILE.exists():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {"content": ""}


def save_file():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -------------------------------
# HTTP ROUTES
# -------------------------------

@app.get("/", response_class=HTMLResponse)
async def home():
    return (BASE_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/load")
async def load():
    return {"content": data["content"]}


# -------------------------------
# WEBSOCKET
# -------------------------------

clients = []


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()
    clients.append(ws)

    try:
        # Send document on connect
        await ws.send_json({
            "content": data["content"]
        })

        while True:

            msg = await ws.receive_json()

            password = msg.get("password", "")
            content = msg.get("content")
            test = msg.get("test", False)

            # -------- AUTH CHECK --------

            if test:

                if password == DEV_PASSWORD:

                    await ws.send_json({
                        "auth": "ok",
                        "password": password
                    })

                else:

                    await ws.send_json({
                        "auth": "fail"
                    })

                continue


            # -------- SAVE CHECK --------

            if password != DEV_PASSWORD:
                continue


            if content is None:
                continue


            # Save
            data["content"] = content
            save_file()


            # Broadcast
            for client in clients:

                try:
                    await client.send_json({
                        "content": content
                    })

                except:
                    pass


    except WebSocketDisconnect:

        if ws in clients:
            clients.remove(ws)


# -------------------------------
# RUN
# -------------------------------

if __name__ == "__main__":

    port = int(os.getenv("PORT", 8000))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
