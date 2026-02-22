import './ChatHistoryItem.css';

export default function ChatHistoryItem({ chat, isActive, onClick }) {
  return (
    <button
      className={`chat-history-item ${isActive ? 'active' : ''}`}
      onClick={onClick}
    >
      <svg
        className="chat-history-item-icon"
        width="16"
        height="16"
        viewBox="0 0 16 16"
        fill="none"
      >
        <path
          d="M2 3.5C2 2.67 2.67 2 3.5 2h9c.83 0 1.5.67 1.5 1.5v7c0 .83-.67 1.5-1.5 1.5H5l-3 3V3.5z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
      <span className="chat-history-item-title">{chat.title}</span>
    </button>
  );
}
