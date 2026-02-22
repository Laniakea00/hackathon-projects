import Logo from './Logo';
import NewChatButton from './NewChatButton';
import ChatHistory from './ChatHistory';
import './Sidebar.css';

export default function Sidebar({
  chats,
  activeChatId,
  onNewChat,
  onSelectChat,
}) {
  return (
    <aside className="sidebar">
      <Logo />
      <NewChatButton onClick={onNewChat} />
      <ChatHistory
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={onSelectChat}
      />
    </aside>
  );
}
