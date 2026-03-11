from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, ingestion_id: int):
        await websocket.accept()
        if ingestion_id not in self.active_connections:
            self.active_connections[ingestion_id] = []
        self.active_connections[ingestion_id].append(websocket)

    def disconnect(self, websocket: WebSocket, ingestion_id: int):
        if ingestion_id in self.active_connections:
            self.active_connections[ingestion_id].remove(websocket)
            if not self.active_connections[ingestion_id]:
                del self.active_connections[ingestion_id]

    async def broadcast(self, ingestion_id: int, message: dict):
        if ingestion_id in self.active_connections:
            for connection in self.active_connections[ingestion_id]:
                await connection.send_json(message)
