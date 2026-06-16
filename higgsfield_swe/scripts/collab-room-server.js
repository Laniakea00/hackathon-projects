/* eslint-disable no-console */
const http = require("http");
const { Server } = require("socket.io");

const PORT = Number(process.env.COLLAB_PORT || 3002);
const HOST = process.env.COLLAB_HOST || "127.0.0.1";

const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }
  res.writeHead(200, { "Content-Type": "text/plain" });
  res.end("ok");
});

const io = new Server(server, {
  cors: { origin: "*", methods: ["GET", "POST"] },
});

const socketRoom = new Map();
const roomMembers = new Map();

const membersOf = (roomId) => {
  if (!roomMembers.has(roomId)) {
    roomMembers.set(roomId, new Set());
  }
  return roomMembers.get(roomId);
};

const emitRoomUsers = (roomId) => {
  io.to(roomId).emit("room-user-change", [...(roomMembers.get(roomId) || [])]);
};

io.on("connection", (socket) => {
  socket.emit("init-room");

  socket.on("join-room", (roomId) => {
    if (!roomId || typeof roomId !== "string") {
      return;
    }
    const members = membersOf(roomId);
    const isFirst = members.size === 0;

    socket.join(roomId);
    socketRoom.set(socket.id, roomId);
    members.add(socket.id);

    if (isFirst) {
      socket.emit("first-in-room");
    } else {
      socket.to(roomId).emit("new-user", socket.id);
    }

    emitRoomUsers(roomId);
  });

  socket.on("server-broadcast", (roomId, encryptedBuffer, iv) => {
    if (socketRoom.get(socket.id) !== roomId) {
      return;
    }
    socket.to(roomId).emit("client-broadcast", encryptedBuffer, iv);
  });

  socket.on("server-volatile-broadcast", (roomId, encryptedBuffer, iv) => {
    if (socketRoom.get(socket.id) !== roomId) {
      return;
    }
    socket.volatile.to(roomId).emit("client-broadcast", encryptedBuffer, iv);
  });

  socket.on("user-follow", () => {
    // noop for hackathon build
  });

  socket.on("disconnect", () => {
    const roomId = socketRoom.get(socket.id);
    if (!roomId) {
      return;
    }
    socketRoom.delete(socket.id);
    const members = roomMembers.get(roomId);
    if (members) {
      members.delete(socket.id);
      if (members.size === 0) {
        roomMembers.delete(roomId);
      } else {
        emitRoomUsers(roomId);
      }
    }
  });
});

server.listen(PORT, HOST, () => {
  console.log(`collab-room-server listening on http://${HOST}:${PORT}`);
});
