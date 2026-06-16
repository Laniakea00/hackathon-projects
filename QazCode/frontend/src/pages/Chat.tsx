import React, { useState, useEffect } from 'react';
import api from '../api/axiosClient';

interface Message {
  id: number;
  sender: 'user' | 'bot';
  content: string;
}

interface Session {
  id: number;
  title: string;
}

export default function Chat() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    if (activeSession) fetchMessages(activeSession);
  }, [activeSession]);

  const fetchSessions = async () => {
    const res = await api.get('/chat/');
    setSessions(res.data);
  };

  const fetchMessages = async (sessionId: number) => {
    const res = await api.get(`/chat/${sessionId}`);
    setMessages(res.data);
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = input;
    setInput('');
    // Optimistic UI update
    setMessages((prev) => [...prev, { id: Date.now(), sender: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const res = await api.post('/chat/', {
        session_id: activeSession,
        content: userMsg,
      });
      setMessages((prev) => [...prev, res.data]);
      if (!activeSession) fetchSessions(); // Refresh sessions if a new one was created
    } catch (error) {
      console.error("Message failed", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar for History */}
      <div className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="p-4 text-xl font-bold border-b border-gray-700">Chat History</div>
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <button 
            onClick={() => {setActiveSession(null); setMessages([])}}
            className="w-full text-left p-2 bg-blue-600 rounded hover:bg-blue-700 mb-4"
          >
            + New Chat
          </button>
          {sessions.map(s => (
            <button 
              key={s.id} 
              onClick={() => setActiveSession(s.id)}
              className={`w-full text-left p-2 rounded truncate ${activeSession === s.id ? 'bg-gray-700' : 'hover:bg-gray-800'}`}
            >
              {s.title}
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`p-4 rounded-lg max-w-xl ${msg.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-white text-gray-800 shadow-sm border'}`}>
                {msg.content}
              </div>
            </div>
          ))}
          {loading && <div className="text-gray-500 italic">Bot is typing...</div>}
        </div>
        
        {/* Input Form */}
        <form onSubmit={sendMessage} className="p-4 bg-white border-t flex gap-4">
          <input
            type="text"
            className="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button type="submit" disabled={loading} className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50">
            Send
          </button>
        </form>
      </div>
    </div>
  );
}