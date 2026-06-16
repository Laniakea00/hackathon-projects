import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { registerSW } from "virtual:pwa-register";

import "../excalidraw-app/sentry";

import { CollabRoom } from "./RoomApp";

window.__EXCALIDRAW_SHA__ = import.meta.env.VITE_APP_GIT_SHA;
const rootElement = document.getElementById("root")!;
const root = createRoot(rootElement);
registerSW();
const path = window.location.pathname;
const roomMatch = path.match(/^\/room\/(.+)/);
const generated = crypto.randomUUID();

root.render(
  <StrictMode>
    <CollabRoom roomId={roomMatch ? roomMatch[1] : generated} />
  </StrictMode>,
);
