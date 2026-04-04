import { useMemo, useRef, useState } from "react";
import { Excalidraw, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw";
import type { ExcalidrawElement } from "@excalidraw/excalidraw/types";
import { ParticipantsPanel } from "./src/components/ParticipantsPanel";
import { useCollabClient } from "./src/hooks/useCollabClient";
import type { Participant } from "./src/types/collab";

const randomColor = () =>
  ["#ef4444", "#22c55e", "#3b82f6", "#a855f7", "#f97316", "#14b8a6"][
    Math.floor(Math.random() * 6)
  ];

const toSimple = (els: readonly ExcalidrawElement[]) =>
  els
    .filter((e) => !e.isDeleted)
    .map((e) => ({
      id: e.id,
      type: e.type,
      x: e.x,
      y: e.y,
      width: e.width,
      height: e.height,
      text: (e as any).text || "",
      color: (e as any).strokeColor || "#000",
    }));

const fromSimple = (arr: any[]): ExcalidrawElement[] =>
  arr.map((o) => ({
    id: o.id,
    type: o.type,
    x: o.x,
    y: o.y,
    width: o.width,
    height: o.height,
    text: o.text || "",
    angle: 0,
    strokeColor: o.color || "#000",
    backgroundColor: "transparent",
    fillStyle: "hachure",
    strokeWidth: 2,
    strokeStyle: "solid",
    roughness: 1,
    opacity: 100,
    groupIds: [],
    boundElements: null,
    locked: false,
    seed: Math.random() * 1000000,
    version: 1,
    versionNonce: Math.random() * 1000000,
    isDeleted: false,
    roundness: { type: 2 },
    baseline: 0,
    fontSize: 20,
    fontFamily: 1,
    textAlign: "left",
    verticalAlign: "top",
    lineHeight: 1.25,
    frameId: null,
    startBinding: null,
    endBinding: null,
  }));

export function CollabRoom({ roomId }: { roomId: string }) {
  const self = useMemo<Participant>(
    () => ({
      id: crypto.randomUUID(),
      name: localStorage.getItem("username") || "Guest",
      color: randomColor(),
      isAI: false,
      active: true,
    }),
    [],
  );

  const apiRef = useRef<ExcalidrawImperativeAPI>(null);
  const [initialData, setInitialData] = useState<any>(null);

  const { participants, send, updateCursor } = useCollabClient(roomId, self, (msg) => {
    if (msg.event === "sync_scene" && msg.user_id !== self.id) {
      const els = fromSimple(msg.payload.objects || []);
      apiRef.current?.updateScene({ elements: els });
    }
  });

  const handleChange = (elements: readonly ExcalidrawElement[]) => {
    send({
      event: "sync_scene",
      room_id: roomId,
      user_id: self.id,
      payload: { objects: toSimple(elements) },
    } as any);
  };

  const handlePointerMove = (evt: any) => {
    updateCursor(evt.clientX, evt.clientY);
  };

  const inviteLink = `${window.location.origin}/room/${roomId}`;

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <div style={{ flex: 1 }} onMouseMove={handlePointerMove}>
        <div style={{ padding: "8px 12px", display: "flex", gap: 8, alignItems: "center" }}>
          <strong>Room:</strong> {roomId}
          <button
            onClick={() => navigator.clipboard.writeText(inviteLink)}
            style={{ padding: "4px 8px" }}
          >
            Copy invite link
          </button>
          <span style={{ fontSize: 12, color: "#555" }}>{inviteLink}</span>
        </div>
        <Excalidraw
          ref={apiRef}
          initialData={initialData || undefined}
          onChange={handleChange}
        />
      </div>
      <ParticipantsPanel participants={participants} />
    </div>
  );
}
