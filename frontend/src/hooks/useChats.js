import { useState, useCallback } from 'react';

let nextChatId = 1;

export function useChats() {
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);

  const createChat = useCallback((firstMessageText) => {
    const id = `chat_${nextChatId++}`;
    const title =
      firstMessageText.length > 30
        ? firstMessageText.slice(0, 30) + '…'
        : firstMessageText;

    const newChat = {
      id,
      title,
      createdAt: new Date().toISOString(),
      messages: [],
    };

    setChats((prev) => [newChat, ...prev]);
    setActiveChatId(id);
    return id;
  }, []);

  const selectChat = useCallback((id) => {
    setActiveChatId(id);
  }, []);

  const updateChatMessages = useCallback((chatId, messages) => {
    setChats((prev) =>
      prev.map((chat) => (chat.id === chatId ? { ...chat, messages } : chat))
    );
  }, []);

  const activeChat = chats.find((c) => c.id === activeChatId) || null;

  const startNewChat = useCallback(() => {
    setActiveChatId(null);
  }, []);

  return {
    chats,
    activeChatId,
    activeChat,
    createChat,
    selectChat,
    startNewChat,
    updateChatMessages,
  };
}
