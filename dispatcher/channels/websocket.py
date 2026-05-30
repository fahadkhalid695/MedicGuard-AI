"""WebSocket notification channel for in-app real-time alerts and vitals streaming."""

import asyncio
import json
from collections import defaultdict
from typing import Optional

import redis.asyncio as redis
import websockets
from websockets.asyncio.server import serve, ServerConnection

from dispatcher.config import REDIS_URL, WS_HOST, WS_PORT


class WebSocketManager:
    """
    Manages WebSocket connections per doctor/user.
    - Doctors connect and register for their patient alerts.
    - Subscribes to Redis Pub/Sub to forward vitals in real-time.
    - Forwards alerts from the dispatcher.
    """

    def __init__(self):
        self._connections: dict[str, set[ServerConnection]] = defaultdict(set)
        self._patient_subscribers: dict[str, set[str]] = defaultdict(set)
        self._all_connections: set[ServerConnection] = set()
        self._server = None
        self._redis_task: Optional[asyncio.Task] = None

    async def start_server(self):
        """Start the WebSocket server and Redis subscriber."""
        self._server = await serve(
            self._handle_connection,
            WS_HOST,
            int(WS_PORT),
        )
        # Start Redis vitals subscriber in background
        self._redis_task = asyncio.create_task(self._subscribe_to_vitals())
        print(f"[WebSocket] Server running on ws://{WS_HOST}:{WS_PORT}")

    async def stop_server(self):
        """Stop the WebSocket server."""
        if self._redis_task:
            self._redis_task.cancel()
            try:
                await self._redis_task
            except asyncio.CancelledError:
                pass
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _subscribe_to_vitals(self):
        """Subscribe to Redis Pub/Sub and forward vitals to all connected dashboards."""
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.psubscribe("vitals:*")
            print("[WebSocket] Subscribed to Redis vitals:* channel")

            async for message in pubsub.listen():
                if message["type"] != "pmessage":
                    continue

                try:
                    data = json.loads(message["data"])
                    patient_id = data.get("patient_id", "")

                    # Build the message for the dashboard
                    ws_message = json.dumps({
                        "type": "vitals_update",
                        "payload": data,
                    })

                    # Send to all connected clients that are subscribed to this patient
                    await self._broadcast_to_patient(patient_id, ws_message)

                except (json.JSONDecodeError, KeyError):
                    pass

        except asyncio.CancelledError:
            await pubsub.punsubscribe()
            await r.aclose()
        except Exception as e:
            print(f"[WebSocket] Redis subscriber error: {e}")

    async def _broadcast_to_patient(self, patient_id: str, message: str):
        """Send a message to all doctors subscribed to a specific patient."""
        doctor_ids = self._patient_subscribers.get(patient_id, set())

        # If no specific subscribers, broadcast to all connected clients
        if not doctor_ids:
            targets = list(self._all_connections)
        else:
            targets = []
            for did in doctor_ids:
                targets.extend(self._connections.get(did, set()))

        dead = []
        for ws in targets:
            try:
                await ws.send(message)
            except (websockets.exceptions.ConnectionClosed, Exception):
                dead.append(ws)

        # Clean up dead connections
        for ws in dead:
            self._all_connections.discard(ws)
            for conns in self._connections.values():
                conns.discard(ws)

    async def _handle_connection(self, websocket: ServerConnection):
        """Handle a new WebSocket connection."""
        doctor_id: Optional[str] = None
        self._all_connections.add(websocket)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue

                # Registration message
                if data.get("type") == "register":
                    doctor_id = data.get("doctor_id", "anonymous")
                    patient_ids = data.get("patient_ids", [])

                    self._connections[doctor_id].add(websocket)
                    for pid in patient_ids:
                        self._patient_subscribers[pid].add(doctor_id)

                    await websocket.send(json.dumps({
                        "type": "registered",
                        "doctor_id": doctor_id,
                        "patients": patient_ids,
                    }))
                    print(f"[WebSocket] Doctor '{doctor_id}' registered for {len(patient_ids)} patients")

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[WebSocket] Connection error: {e}")
        finally:
            self._all_connections.discard(websocket)
            if doctor_id:
                self._connections[doctor_id].discard(websocket)
                if not self._connections[doctor_id]:
                    del self._connections[doctor_id]
                    for subs in self._patient_subscribers.values():
                        subs.discard(doctor_id)

    async def send_to_patient_subscribers(self, patient_id: str, payload: dict) -> list[str]:
        """Send an alert notification to all doctors subscribed to a patient."""
        notified = []
        message = json.dumps({
            "type": "alert",
            "payload": payload,
        })

        doctor_ids = self._patient_subscribers.get(patient_id, set())

        # Also broadcast alerts to all connections if no specific subscribers
        if not doctor_ids:
            targets = list(self._all_connections)
        else:
            targets = []
            for did in doctor_ids:
                targets.extend(self._connections.get(did, set()))
                notified.append(did)

        dead = []
        for ws in targets:
            try:
                await ws.send(message)
            except (websockets.exceptions.ConnectionClosed, Exception):
                dead.append(ws)

        for ws in dead:
            self._all_connections.discard(ws)
            for conns in self._connections.values():
                conns.discard(ws)

        return notified


# Singleton instance
ws_manager = WebSocketManager()


async def send_ws_notification(patient_id: str, payload: dict) -> list[str]:
    """Send a WebSocket notification to all subscribers of a patient."""
    return await ws_manager.send_to_patient_subscribers(patient_id, payload)
