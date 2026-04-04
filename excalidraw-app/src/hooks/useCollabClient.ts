import { useEffect, useRef, useState } from "react";
import type { CollabEvent, Participant, Cursor } from "../types/collab";

const runtimeWs = () => {
  const envUrl = import.meta.env.VITE_WS_URL as string | undefined;
  if (envUrl) return envUrl;
  const { protocol, hostname } = window.location;
  const wsProto = protocol === "https:" ? "wss:" : "ws:";
  return `${wsProto}//${hostname}:8010/ws`;
};

export function useCollabClient(roomId: string, self: Participant, onEvent?: (msg: any) => void) {
  const [participants, setParticipants] = useState<Participant[]>([self]);
  const [cursors, setCursors] = useState<Record<string, Cursor>>({});
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`${runtimeWs()}/${roomId}?user_id=${self.id}`);
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data) as CollabEvent | any;
      onEvent?.(msg);
      if (msg.event === "user_join") {
        setParticipants((prev) => {
          if (prev.find((p) => p.id === msg.payload.user_id)) return prev;
          return [
            ...prev,
            {
              id: msg.payload.user_id,
              name: msg.payload.name || msg.payload.user_id,
              color: msg.payload.color || "#888",
              isAI: !!msg.payload.isAI,
              active: true,
            },
          ];
        });
      } else if (msg.event === "user_leave") {
        setParticipants((prev) => prev.filter((p) => p.id !== msg.payload.user_id));
        setCursors((prev) => {
          const next = { ...prev };
          delete next[msg.payload.user_id];
          return next;
        });
      } else if (msg.event === "cursor") {
        setCursors((prev) => ({
          ...prev,
          [msg.user_id]: {
            userId: msg.user_id,
            x: msg.payload.x,
            y: msg.payload.y,
            color: participants.find((p) => p.id === msg.user_id)?.color || "#888",
          },
        }));
      }
      // Canvas events are handled in Excalidraw integration layer
    };

    return () => {
      ws.close();
    };
  }, [roomId, self.id]);

  const send = (event: CollabEvent) => {
    wsRef.current?.readyState === WebSocket.OPEN && wsRef.current.send(JSON.stringify(event));
  };

  const updateCursor = (x: number, y: number) =>
    send({ event: "cursor", room_id: roomId, user_id: self.id, payload: { x, y } });

  return { participants, cursors, send, updateCursor, wsRef };
}
