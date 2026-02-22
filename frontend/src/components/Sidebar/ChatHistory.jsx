import ChatHistoryItem from './ChatHistoryItem';
import './ChatHistory.css';

export default function ChatHistory({ chats, activeChatId, onSelectChat }) {
  if (chats.length === 0) {
    return (
      <div className="chat-history">
        <div className="chat-history-label">История чатов</div>
        <p className="chat-history-empty">Пока нет чатов</p>
      </div>
    );
  }

  return (
    <div className="chat-history">
      <div className="chat-history-label">История чатов</div>
      <div className="chat-history-list">
        {chats.map((chat) => (
          <ChatHistoryItem
            key={chat.id}
            chat={chat}
            isActive={chat.id === activeChatId}
            onClick={() => onSelectChat(chat.id)}
          />
        ))}
      </div>
    </div>
  );
}
