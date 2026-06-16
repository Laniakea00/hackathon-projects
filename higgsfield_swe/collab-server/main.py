"""
Minimal real-time collab backend for Excalidraw-style canvas.
Run: uvicorn collab-server.main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import secrets
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------- Data models ----------


class CanvasObject(BaseModel):
    id: str
    type: str  # rect|circle|line|text
    x: float
    y: float
    width: float = 0
    height: float = 0
    text: Optional[str] = ""
    color: Optional[str] = "#000"


class WSMessage(BaseModel):
    event: str
    room_id: str
    user_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)


# ---------- In-memory state ----------


class Room:
    def __init__(self, room_id: str):
        self.id = room_id
        self.canvas: Dict[str, CanvasObject] = {}
        self.users: Dict[str, WebSocket] = {}
        self.lock = asyncio.Lock()


rooms: Dict[str, Room] = {}

# ---------- Helpers ----------


async def broadcast(room: Room, message: Dict[str, Any]) -> None:
    data = json.dumps(message)
    dead: List[str] = []
    for uid, ws in room.users.items():
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(uid)
    for uid in dead:
        room.users.pop(uid, None)


async def handle_join(room: Room, user_id: str, ws: WebSocket) -> None:
    async with room.lock:
        room.users[user_id] = ws
        # send current state to newcomer
        await ws.send_text(
            json.dumps(
                {
                    "event": "room_state",
                    "room_id": room.id,
                    "payload": {"objects": [obj.model_dump() for obj in room.canvas.values()]},
                }
            )
        )
    await broadcast(
        room,
        {"event": "user_join", "room_id": room.id, "payload": {"user_id": user_id}},
    )


async def handle_leave(room: Room, user_id: str) -> None:
    async with room.lock:
        room.users.pop(user_id, None)
    await broadcast(
        room,
        {"event": "user_leave", "room_id": room.id, "payload": {"user_id": user_id}},
    )


async def handle_object(room: Room, msg: WSMessage) -> None:
    event = msg.event
    payload = msg.payload
    if event == "add_object":
        obj = CanvasObject(**payload["object"])
        async with room.lock:
            room.canvas[obj.id] = obj
    elif event == "update_object":
        obj = CanvasObject(**payload["object"])
        async with room.lock:
            room.canvas[obj.id] = obj
    elif event == "remove_object":
        obj_id = payload["object_id"]
        async with room.lock:
            room.canvas.pop(obj_id, None)
    elif event == "sync_scene":
        objs = [CanvasObject(**o) for o in payload.get("objects", [])]
        async with room.lock:
            room.canvas = {o.id: o for o in objs}
    else:
        return

    await broadcast(room, msg.model_dump())


# ---------- FastAPI app ----------

app = FastAPI(title="Collab Canvas API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str = ""):
    await websocket.accept()
    user_id = user_id or secrets.token_hex(4)
    room = rooms.setdefault(room_id, Room(room_id))

    await handle_join(room, user_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            msg = WSMessage.model_validate_json(raw)
            if msg.event == "leave_room":
                await handle_leave(room, msg.user_id)
                break
            elif msg.event in {"add_object", "update_object", "remove_object"}:
                await handle_object(room, msg)
    except WebSocketDisconnect:
        await handle_leave(room, user_id)
    except Exception:
        await handle_leave(room, user_id)
        raise


# ---------- Simple AI stub (connect separately) ----------

async def ai_stub(room_id: str):
    """
    Example AI loop: logs canvas state; could be expanded to call Claude/OpenAI.
    """
    import websockets

    uri = f"ws://localhost:8000/ws/{room_id}?user_id=ai-bot"
    async with websockets.connect(uri) as ws:
        state = await ws.recv()
        print("AI got state:", state)
        # send a sample rectangle
        await ws.send(
            json.dumps(
                {
                    "event": "add_object",
                    "room_id": room_id,
                    "user_id": "ai-bot",
                    "payload": {
                        "object": {
                            "id": secrets.token_hex(8),
                            "type": "rect",
                            "x": 50,
                            "y": 50,
                            "width": 120,
                            "height": 80,
                            "color": "#ff9900",
                        }
                    },
                }
            )
        )

# For manual AI run:
# asyncio.run(ai_stub("demo-room"))
