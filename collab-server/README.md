# Collab Server (prototype)

FastAPI + WebSocket сервер для синхронной работы с канвасом.

## Быстрый старт
```bash
cd collab-server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## WebSocket API
`ws://localhost:8000/ws/<room_id>?user_id=<your-id>`

Сообщения — JSON:
```json
{
  "event": "add_object|update_object|remove_object|leave_room",
  "room_id": "room-123",
  "user_id": "alice",
  "payload": {
    "object": { "id": "...", "type": "rect", "x": 0, "y": 0, "width": 50, "height": 30, "text": "", "color": "#000" },
    "object_id": "..."
  }
}
```

Сервер рассылает всем участникам исходное сообщение, а также:
- `room_state` при входе: `payload.objects` — массив объектов.
- `user_join` / `user_leave` с `payload.user_id`.

## AI-участник
В `main.py` есть `ai_stub` — пример подключенного бота. Его можно заменить вызовом Claude/OpenAI: бот получает `room_state`, генерирует действие и шлёт `add_object|update_object`.

## Мини-клиент (псевдокод)
```js
const ws = new WebSocket("ws://localhost:8000/ws/room-1?user_id=alice");
ws.onmessage = (ev) => { const msg = JSON.parse(ev.data); /* обновить канвас */ };
ws.send(JSON.stringify({
  event: "add_object",
  room_id: "room-1",
  user_id: "alice",
  payload: { object: { id: crypto.randomUUID(), type:"rect", x:10,y:10,width:80,height:40,color:"#000" } }
}));
```

## Следующие шаги
- Поднять Redis вместо in-memory для прод.
- Добавить simple auth (JWT header → `user_id`).
- Оборачивать события канваса в CRDT/OT при необходимости.
- Интегрировать с фронтом на Excalidraw: отправлять `AppState` диффы или минимальный JSON-формат выше.
