import './NewChatButton.css';

export default function NewChatButton({ onClick }) {
  return (
    <button className="new-chat-btn" onClick={onClick}>
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <path
          d="M9 3v12M3 9h12"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
      Новый чат
    </button>
  );
}
