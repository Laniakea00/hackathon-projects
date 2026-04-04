/* eslint-disable no-console */
const http = require("http");
const { Server } = require("socket.io");

const PORT = Number(process.env.COLLAB_PORT || 3002);
const HOST = process.env.COLLAB_HOST || "0.0.0.0";

const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }
  res.writeHead(200, { "Content-Type": "text/plain" });
  res.end("collab-room-server");
});

const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"],
  },
});

const socketToRoom = new Map();
const roomMembers = new Map();
const followerToTargetByRoom = new Map();
const followersByTargetByRoom = new Map();

const getRoomMembers = (roomId) => {
  if (!roomMembers.has(roomId)) {
    roomMembers.set(roomId, new Set());
  }
  return roomMembers.get(roomId);
};

const getFollowerToTarget = (roomId) => {
  if (!followerToTargetByRoom.has(roomId)) {
    followerToTargetByRoom.set(roomId, new Map());
  }
  return followerToTargetByRoom.get(roomId);
};

const getFollowersByTarget = (roomId) => {
  if (!followersByTargetByRoom.has(roomId)) {
    followersByTargetByRoom.set(roomId, new Map());
  }
  return followersByTargetByRoom.get(roomId);
};

const emitRoomUsers = (roomId) => {
  const members = [...(roomMembers.get(roomId) || new Set())];
  io.to(roomId).emit("room-user-change", members);
};

const emitFollowersForTarget = (roomId, targetSocketId) => {
  const followersByTarget = getFollowersByTarget(roomId);
  const followers = [...(followersByTarget.get(targetSocketId) || new Set())];
  io.to(targetSocketId).emit("user-follow-room-change", followers);
};

const removeFollower = (roomId, followerSocketId) => {
  const followerToTarget = getFollowerToTarget(roomId);
  const followersByTarget = getFollowersByTarget(roomId);
  const prevTarget = followerToTarget.get(followerSocketId);
  if (!prevTarget) {
    return;
  }
  followerToTarget.delete(followerSocketId);
  const prevFollowers = followersByTarget.get(prevTarget);
  if (prevFollowers) {
    prevFollowers.delete(followerSocketId);
    if (prevFollowers.size === 0) {
      followersByTarget.delete(prevTarget);
    }
  }
  emitFollowersForTarget(roomId, prevTarget);
};

io.on("connection", (socket) => {
  socket.emit("init-room");

  socket.on("join-room", (roomId) => {
    if (!roomId || typeof roomId !== "string") {
      return;
    }

    const members = getRoomMembers(roomId);
    const wasFirst = members.size === 0;

    socket.join(roomId);
    socketToRoom.set(socket.id, roomId);
    members.add(socket.id);

    if (wasFirst) {
      socket.emit("first-in-room");
    } else {
      socket.to(roomId).emit("new-user", socket.id);
    }

    emitRoomUsers(roomId);
  });

  socket.on("server-broadcast", (roomId, encryptedBuffer, iv) => {
    if (socketToRoom.get(socket.id) !== roomId) {
      return;
    }
    socket.to(roomId).emit("client-broadcast", encryptedBuffer, iv);
  });

  socket.on("server-volatile-broadcast", (roomId, encryptedBuffer, iv) => {
    if (socketToRoom.get(socket.id) !== roomId) {
      return;
    }
    socket.volatile.to(roomId).emit("client-broadcast", encryptedBuffer, iv);
  });

  socket.on("user-follow", (payload) => {
    const roomId = socketToRoom.get(socket.id);
    if (!roomId) {
      return;
    }

    const targetSocketId = payload?.userToFollow?.socketId;
    const action = payload?.action;

    removeFollower(roomId, socket.id);

    if (action === "FOLLOW" && typeof targetSocketId === "string") {
      const members = roomMembers.get(roomId);
      if (!members || !members.has(targetSocketId)) {
        return;
      }
      const followerToTarget = getFollowerToTarget(roomId);
      const followersByTarget = getFollowersByTarget(roomId);
      followerToTarget.set(socket.id, targetSocketId);

      if (!followersByTarget.has(targetSocketId)) {
        followersByTarget.set(targetSocketId, new Set());
      }
      followersByTarget.get(targetSocketId).add(socket.id);
      emitFollowersForTarget(roomId, targetSocketId);
    }
  });

  socket.on("disconnect", () => {
    const roomId = socketToRoom.get(socket.id);
    if (!roomId) {
      return;
    }

    socketToRoom.delete(socket.id);
    removeFollower(roomId, socket.id);

    const followersByTarget = getFollowersByTarget(roomId);
    const followerToTarget = getFollowerToTarget(roomId);

    const followersOfDisconnected = followersByTarget.get(socket.id);
    if (followersOfDisconnected) {
      for (const followerSocketId of followersOfDisconnected) {
        followerToTarget.delete(followerSocketId);
      }
      followersByTarget.delete(socket.id);
    }

    const members = roomMembers.get(roomId);
    if (members) {
      members.delete(socket.id);
      if (members.size === 0) {
        roomMembers.delete(roomId);
        followerToTargetByRoom.delete(roomId);
        followersByTargetByRoom.delete(roomId);
      } else {
        emitRoomUsers(roomId);
      }
    }
  });
});

server.listen(PORT, HOST, () => {
  console.log(`collab-room-server listening on http://${HOST}:${PORT}`);
});
