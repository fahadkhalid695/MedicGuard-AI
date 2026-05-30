"""WebSocket notification channel for in-app real-time alerts."""

import asyncio
import json
from collections import defaultdict
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

from dispatcher.config import WS_HOST, WS_PORT


class WebSocketManager:
    """
    Manages WebSocket connections per doctor/user.
    Doctors connect and register for their patient alerts.
    """

    def __init__(self):
        # Map: doctor_id -> set of active WebSocket connections
        self._connections: dict[str, set[WebSocketServerProtocol]] = defaultdict(set)
        # Map: patient_id -> set of doctor_ids subscribed to that patient
        self._patient_subscribers: dict[str, set[str]] = defaultdict(set)
        self._server = None

    async def start_server(self):
        """Start the WebSocket server."""
        self._server = await websockets.serve(
            self._handle_connection,
            WS_HOST,
            WS_PORT,
        )
        print(f"[WebSocket] Server running on ws://{WS_HOST}:{WS_PORT}")

    async def stop_server(self):
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_connection(self, websocket: WebSocketServerProtocol):
        """Handle a new WebSocket connection."""
        doctor_id: Optional[str] = None

        try:
            async for message in websocket:
                data = json.loads(message)

                # Registration message: {"type": "register", "doctor_id": "...", "patient_ids": [...]}
                if data.get("type") == "register":
                    doctor_id = data["doctor_id"]
                    patient_ids = data.get("patient_ids", [])

                    self._connections[doctor_id].add(websocket)
                    for pid in patient_ids:
                        self._patient_subscribers[pid].add(doctor_id)

                    await websocket.send(json.dumps({
                        "type": "registered",
                        "doctor_id": doctor_id,
                        "patients": patient_ids,
                    }))

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Clean up on disconnect
            if doctor_id:
                self._connections[doctor_id].discard(websocket)
                if not self._connections[doctor_id]:
                    del self._connections[doctor_id]
                    # Remove from patient subscriptions
                    for subs in self._patient_subscribers.values():
                        subs.discard(doctor_id)

    async def send_to_patient_subscribers(self, patient_id: str, payload: dict) -> list[str]:
        """
        Send a notification to all doctors subscribed to a patient.
        Returns list of doctor_ids that were notified.
        """
        notified = []
        doctor_ids = self._patient_subscribers.get(patient_id, set())

        message = json.dumps({
            "type": "alert",
            "payload": payload,
        })

        for doctor_id in doctor_ids:
            connections = self._connections.get(doctor_id, set())
            dead_connections = set()

            for ws in connections:
                try:
                    await ws.send(message)
                    if doctor_id not in notified:
                        notified.append(doctor_id)
                except websockets.exceptions.ConnectionClosed:
                    dead_connections.add(ws)

            # Clean up dead connections
            for ws in dead_connections:
                connections.discard(ws)

        return notified


# Singleton instance
ws_manager = WebSocketManager()


async def send_ws_notification(patient_id: str, payload: dict) -> list[str]:
    """Send a WebSocket notification to all subscribers of a patient."""
    return await ws_manager.send_to_patient_subscribers(patient_id, payload)
