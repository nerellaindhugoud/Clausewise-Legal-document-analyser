from typing import Dict, List, Any 
from collections import defaultdict

class Room: 
    def __init__(self): 
        self.clients: List[Any] = [] 
        self.state: Dict[str, Any] = {"document": "", "chat": []}

class CollabManager: 
    def __init__(self): 
        self.rooms: Dict[str, Room] = defaultdict(Room)

    async def join(self, room_id: str, ws):
      room = self.rooms[room_id]
      room.clients.append(ws)
      await ws.send_json({"type": "state", "payload": room.state})

    async def leave(self, room_id: str, ws):
      if ws in room.clients:
        room.clients.remove(ws)

    async def broadcast(self, room_id: str, message: Dict[str, Any]):
      room = self.rooms[room_id]
      dead = []
      for c in room.clients:
        try:
            await c.send_json(message)
        except Exception:
            dead.append(c)
      for d in dead:
        if d in room.clients:
            room.clients.remove(d)

    async def update_document(self, room_id: str, content: str):
      room = self.rooms[room_id]
      room.state["document"] = content
      await self.broadcast(room_id, {"type": "document", "payload": content})

    async def add_chat(self, room_id: str, user: str, text: str):
       room = self.rooms[room_id]
       entry = {"user": user, "text": text}
       room.state["chat"].append(entry)
       await self.broadcast(room_id, {"type": "chat", "payload": entry})

COLLAB = CollabManager()
