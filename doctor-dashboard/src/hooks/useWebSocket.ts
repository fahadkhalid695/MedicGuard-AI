import { useCallback, useEffect, useRef, useState } from "react";
import type { WSMessage } from "../types";

// Use the same hostname as the page (works on EC2, localhost, anywhere)
const WS_URL = `ws://${window.location.hostname}:8765`;

interface UseWebSocketOptions {
  doctorId: string;
  patientIds: string[];
  onMessage: (msg: WSMessage) => void;
}

export function useWebSocket({ doctorId, patientIds, onMessage }: UseWebSocketOptions) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Register with the server
      ws.send(
        JSON.stringify({
          type: "register",
          doctor_id: doctorId,
          patient_ids: patientIds,
        })
      );
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSMessage;
        onMessage(data);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
      // Reconnect after 3 seconds
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [doctorId, patientIds, onMessage]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected };
}
