import './UserMessage.css';

export default function UserMessage({ text }) {
  return (
    <div className="user-message-wrapper">
      <div className="user-message">{text}</div>
    </div>
  );
}
