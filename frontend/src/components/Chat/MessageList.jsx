import { useEffect, useRef } from 'react';
import UserMessage from './UserMessage';
import AiResponse from './AiResponse';
import LoadingIndicator from './LoadingIndicator';
import './MessageList.css';

export default function MessageList({ messages, isLoading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="message-list">
      {messages.map((msg) =>
        msg.role === 'user' ? (
          <UserMessage key={msg.id} text={msg.text} />
        ) : (
          <AiResponse key={msg.id} diagnoses={msg.diagnoses} />
        )
      )}
      {isLoading && <LoadingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
