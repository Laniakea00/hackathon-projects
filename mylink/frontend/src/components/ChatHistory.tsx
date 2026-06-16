import { useState, useEffect } from 'react'
import { api } from '../lib/api'

interface Message {
  id: string
  sender_type: 'bot' | 'candidate'
  message_text: string
  created_at: string
}

interface ChatHistoryData {
  id: string
  response_id: string
  started_at: string
  ended_at: string | null
  messages: Message[]
}

export default function ChatHistory({ responseId }: { responseId: string }) {
  const [chatData, setChatData] = useState<ChatHistoryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchChat = async () => {
      try {
        setLoading(true)
        const res = await api.get(`/responses/${responseId}/chat`)
        setChatData(res.data)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load chat history')
      } finally {
        setLoading(false)
      }
    }

    if (responseId) {
      fetchChat()
    }
  }, [responseId])

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    )
  }

  if (error || !chatData) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-red-600">
          {error || 'Chat history not available'}
        </div>
      </div>
    )
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-6 text-white">
        <h2 className="text-2xl font-bold">История чата</h2>
        <p className="text-blue-100 mt-1">
          Начало: {new Date(chatData.started_at).toLocaleString('ru-RU')}
          {chatData.ended_at && ` | Завершено: ${new Date(chatData.ended_at).toLocaleString('ru-RU')}`}
        </p>
      </div>

      {/* Messages */}
      <div className="p-6 space-y-4 max-h-[600px] overflow-y-auto">
        {chatData.messages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            Чат еще не начался
          </div>
        ) : (
          chatData.messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.sender_type === 'candidate' ? 'justify-end' : 'justify-start'}`}
            >
              <div className="flex items-start gap-3 max-w-[80%]">
                {msg.sender_type === 'bot' && (
                  <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                )}
                
                <div className="flex flex-col gap-1">
                  <div
                    className={`rounded-2xl px-4 py-3 ${
                      msg.sender_type === 'candidate'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <p className="text-sm leading-relaxed">{msg.message_text}</p>
                  </div>
                  <span className={`text-xs text-gray-500 ${msg.sender_type === 'candidate' ? 'text-right' : 'text-left'}`}>
                    {formatTime(msg.created_at)}
                  </span>
                </div>

                {msg.sender_type === 'candidate' && (
                  <div className="w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer Stats */}
      <div className="border-t bg-gray-50 p-4">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>Всего сообщений: {chatData.messages.length}</span>
          <span>
            Вопросов бота: {chatData.messages.filter(m => m.sender_type === 'bot').length} | 
            Ответов кандидата: {chatData.messages.filter(m => m.sender_type === 'candidate').length}
          </span>
        </div>
      </div>
    </div>
  )
}

