import { useState, useCallback, useRef } from 'react';
import { getDiagnoses } from '../services/diagnosisService';

let nextMsgId = 1;

export function useMessages() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const loadMessages = useCallback((msgs) => {
    setMessages(msgs || []);
  }, []);

  const sendMessage = useCallback(async (text) => {
    const userMsg = {
      id: nextMsgId++,
      role: 'user',
      text,
    };

    const afterUser = [...messagesRef.current, userMsg];
    setMessages(afterUser);
    setIsLoading(true);

    try {
      const diagnoses = await getDiagnoses(text);
      const aiMsg = {
        id: nextMsgId++,
        role: 'assistant',
        diagnoses,
      };
      const afterAi = [...afterUser, aiMsg];
      setMessages(afterAi);
      return afterAi;
    } catch {
      const errorMsg = {
        id: nextMsgId++,
        role: 'assistant',
        diagnoses: [
          {
            rank: 1,
            name: 'Ошибка',
            icd10: '—',
            description: 'Не удалось получить ответ. Попробуйте ещё раз.',
          },
        ],
      };
      const afterError = [...afterUser, errorMsg];
      setMessages(afterError);
      return afterError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, isLoading, sendMessage, loadMessages, clearMessages };
}
