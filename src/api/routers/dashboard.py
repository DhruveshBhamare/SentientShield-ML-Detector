import asyncio
import sqlite3
import json
import os
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from ...configs.security import auth_dependency
from ...configs.config import LOG_DIR

router = APIRouter(prefix="/api", tags=["Dashboard"])
INTEL_DB_PATH = os.path.join(LOG_DIR, "intelligence.db")

@router.get("/intel/reports")
async def get_intel_reports(limit: int = 10, user: Dict = Depends(auth_dependency)):
    if not os.path.exists(INTEL_DB_PATH):
        return []
    
    conn = sqlite3.connect(INTEL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM soc_reports ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


async def _threat_simulator_loop():
    while True:
        await asyncio.sleep(2.5)
        await manager.broadcast({
            "type": "threat_update",
            "severity": "info",
            "message": "Heartbeat",
        })


@router.on_event("startup")
async def _start_loop():
    asyncio.create_task(_threat_simulator_loop())


@router.websocket("/ws/realtime")
async def ws_realtime(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/health")
async def health(user: Dict = Depends(auth_dependency)):
    return {"status": "ok", "user": user.get("sub") or user.get("uid")}