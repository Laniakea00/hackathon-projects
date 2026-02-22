import WelcomeScreen from './WelcomeScreen';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import Disclaimer from './Disclaimer';
import './ChatArea.css';

export default function ChatArea({ messages, isLoading, onSend }) {
  const hasMessages = messages.length > 0;

  return (
    <div className="chat-area">
      {hasMessages ? (
        <MessageList messages={messages} isLoading={isLoading} />
      ) : (
        <WelcomeScreen />
      )}
      <ChatInput onSend={onSend} disabled={isLoading} />
      <Disclaimer />
    </div>
  );
}
