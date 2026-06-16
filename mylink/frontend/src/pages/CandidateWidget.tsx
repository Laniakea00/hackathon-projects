import { useEffect, useRef, useState } from 'react'
import { api, wsUrl } from '../lib/api'

// PreChatScreen Component
function PreChatScreen({
  isOpen,
  onStart,
  onCancel
}: {
  isOpen: boolean
  onStart: (language: string, consent: boolean) => void
  onCancel: () => void
}) {
  const [selectedLanguage, setSelectedLanguage] = useState('ru')
  const [consentGiven, setConsentGiven] = useState(false)

  if (!isOpen) return null

  const handleStart = () => {
    if (consentGiven) {
      onStart(selectedLanguage, consentGiven)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-semibold mb-4">Пройти мини-собеседование</h2>

        <div className="mb-6">
          <p className="text-gray-600 mb-4">
            Перед началом собеседования выберите язык и подтвердите согласие на обработку данных.
          </p>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Выберите язык</label>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="w-full border rounded px-3 py-2"
            >
              <option value="ru">Русский</option>
              <option value="kk">Қазақша</option>
              <option value="en">English</option>
            </select>
          </div>

          <div className="mb-4">
            <label className="flex items-start">
              <input
                type="checkbox"
                checked={consentGiven}
                onChange={(e) => setConsentGiven(e.target.checked)}
                className="mt-1 mr-2"
              />
              <span className="text-sm text-gray-700">
                Я согласен на обработку моих данных в соответствии с политикой конфиденциальности
              </span>
            </label>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleStart}
            disabled={!consentGiven}
            className={`flex-1 ${!consentGiven ? 'bg-gray-300' : 'bg-blue-600 hover:bg-blue-700'} text-white px-4 py-2 rounded`}
          >
            Начать (~2 мин)
          </button>
          <button
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
          >
            Отмена
          </button>
        </div>
      </div>
    </div>
  )
}

// ChatModal Component
function ChatModal({
  isOpen,
  onClose,
  messages,
  chatState,
  input,
  setInput,
  onSendMessage,
  onKeyPress,
  onPause,
  onCancel
}: {
  isOpen: boolean
  onClose: () => void
  messages: { sender: 'bot' | 'me', text: string }[]
  chatState: any
  input: string
  setInput: (value: string) => void
  onSendMessage: () => void
  onKeyPress: (e: React.KeyboardEvent) => void
  onPause: () => void
  onCancel: () => void
}) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-4xl h-[80vh] flex flex-col m-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Мини-собеседование</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            ×
          </button>
        </div>

        {/* Progress and Score Display */}
        {!chatState.isCompleted && chatState.totalQuestions > 0 && (
          <div className="bg-gray-50 p-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-3">
                <span className="font-medium">
                  Прогресс: {chatState.questionIndex + 1} / {chatState.totalQuestions}
                </span>
                <span className="text-gray-600">
                  ≈ {chatState.estimatedTimeMinutes} мин
                </span>
              </div>
              {chatState.currentScore > 0 && (
                <span className={`font-medium px-2 py-1 rounded text-xs ${
                  chatState.currentScore >= 70 ? 'bg-green-100 text-green-800' :
                  chatState.currentScore >= 50 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  Оценка: {chatState.currentScore}%
                </span>
              )}
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(chatState.questionIndex / chatState.totalQuestions) * 100}%` }}
              ></div>
            </div>
            {/* Action buttons */}
            {!chatState.isPaused && (
              <div className="flex gap-2 justify-end">
                <button
                  onClick={onPause}
                  className="text-sm px-3 py-1 text-gray-600 hover:text-gray-800"
                >
                  ⏸ Приостановить
                </button>
                <button
                  onClick={onCancel}
                  className="text-sm px-3 py-1 text-red-600 hover:text-red-800"
                >
                  ✕ Отменить
                </button>
              </div>
            )}
          </div>
        )}

        {/* Final Results */}
        {chatState.isCompleted && (
          <div className="bg-gray-50 p-4 space-y-2">
            <h3 className="font-medium text-gray-900">Собеседование завершено!</h3>
            <div className="flex items-center gap-4">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                chatState.verdict === 'подходит' ? 'bg-green-100 text-green-800' :
                chatState.verdict === 'сомнительно' ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {chatState.verdict === 'подходит' ? '✅ Подходит' :
                 chatState.verdict === 'сомнительно' ? '⚠️ Сомнительно' : '❌ Не подходит'}
              </span>
              <span className="text-lg font-bold text-gray-900">
                Итоговая оценка: {chatState.finalScore}%
              </span>
            </div>
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-auto p-4 space-y-3">
          {messages.map((message, i) => (
            <div key={i} className={`flex ${message.sender === 'me' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                message.sender === 'me'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}>
                {message.text}
              </div>
            </div>
          ))}
          {messages.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              Ожидание вопросов...
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t">
          <div className="flex gap-2">
            <input
              className="flex-1 border rounded px-3 py-2"
              placeholder={chatState.isCompleted ? "Собеседование завершено" : "Введите ваш ответ..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyPress}
              disabled={chatState.isCompleted}
            />
            <button
              onClick={onSendMessage}
              disabled={!input.trim() || chatState.isCompleted}
              className={`px-4 py-2 rounded ${
                !input.trim() || chatState.isCompleted
                  ? 'bg-gray-300 text-gray-500'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              Отправить
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function CandidateWidget() {
  const [fullName, setFullName] = useState('Ivan Ivanov')
  const [email, setEmail] = useState('ivan@example.com')
  const [phone, setPhone] = useState('+79990000000')
  const [city, setCity] = useState('Moscow')
  const [resumeText, setResumeText] = useState('Experienced Python developer...')

  const [candidateId, setCandidateId] = useState<string>('')
  const [vacancyId, setVacancyId] = useState<string>('')
  const [responseId, setResponseId] = useState<string>('')

  // Modal and pre-chat state
  const [showPreChat, setShowPreChat] = useState(false)
  const [showChatModal, setShowChatModal] = useState(false)

  const [messages, setMessages] = useState<{ sender: 'bot' | 'me', text: string }[]>([])
  const [chatState, setChatState] = useState({
    questionIndex: 0,
    totalQuestions: 0,
    currentScore: 0,
    isCompleted: false,
    isPaused: false,
    verdict: '',
    finalScore: 0,
    estimatedTimeMinutes: 2
  })
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<number | null>(null)

  const inputCls = 'border rounded px-3 py-2 w-full'
  const btnCls = 'inline-flex items-center gap-2 rounded bg-blue-600 text-white px-3 py-2 text-sm hover:bg-blue-700 disabled:opacity-50'

  const createCandidate = async () => {
    const res = await api.post(`/candidates`, {
      full_name: fullName,
      email,
      phone,
      city,
      resume_text: resumeText,
    })
    setCandidateId(res.data.id)
  }

  const createResponse = async () => {
    if (!candidateId || !vacancyId) return
    const res = await api.post(`/responses`, {
      candidate_id: candidateId,
      vacancy_id: vacancyId,
    })
    setResponseId(res.data.id)
  }

  const scheduleReconnect = () => {
    if (reconnectAttempts.current >= 5) return
    const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttempts.current))
    reconnectAttempts.current += 1
    reconnectTimer.current = window.setTimeout(() => connectWs(), delay)
  }

  const handlePreChatStart = (language: string, consent: boolean) => {
    setShowPreChat(false)
    setShowChatModal(true)
    // Update response with language preference (if needed)
    connectWs()
  }

  const handlePreChatCancel = () => {
    setShowPreChat(false)
  }

  const handleModalClose = () => {
    setShowChatModal(false)
    // Clean up WebSocket connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    // Reset chat state
    setMessages([])
    setChatState({
      questionIndex: 0,
      totalQuestions: 0,
      currentScore: 0,
      isCompleted: false,
      isPaused: false,
      verdict: '',
      finalScore: 0,
      estimatedTimeMinutes: 2
    })
  }

  const handlePauseChat = () => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({ type: 'pause' }))
    setChatState(prev => ({ ...prev, isPaused: true }))
  }

  const handleCancelChat = () => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({ type: 'cancel' }))
  }

  const connectWs = () => {
    if (!responseId) return
    if (wsRef.current) {
      try { wsRef.current.close() } catch {}
    }
    const url = wsUrl(`/ws/chat/${responseId}`)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      reconnectAttempts.current = 0
      setMessages(prev => [...prev, { sender: 'bot', text: 'Соединение установлено. Ожидание вопросов...' }])
    }
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'bot_message' && data.message) {
          setMessages(prev => [...prev, { sender: 'bot', text: data.message }])

          // Calculate estimated time (30 seconds per question)
          const remaining = (data.total_questions || 0) - (data.question_index || 0) - 1
          const estimatedMinutes = Math.max(1, Math.ceil((remaining * 30) / 60))

          // Update chat state
          setChatState(prev => ({
            ...prev,
            questionIndex: data.question_index || prev.questionIndex,
            totalQuestions: data.total_questions || prev.totalQuestions,
            currentScore: data.current_score || prev.currentScore,
            estimatedTimeMinutes: estimatedMinutes,
            isCompleted: false
          }))
        } else if (data.type === 'chat_ended') {
          setMessages(prev => [...prev, {
            sender: 'bot',
            text: `Чат завершен. Оценка: ${data.final_score || 0}%, Вердикт: ${data.verdict || 'Неизвестно'}`
          }])

          setChatState(prev => ({
            ...prev,
            isCompleted: true,
            verdict: data.verdict || prev.verdict,
            finalScore: data.final_score || prev.finalScore
          }))
        } else if (data.type === 'chat_paused') {
          setMessages(prev => [...prev, { sender: 'bot', text: data.message || 'Собеседование приостановлено' }])
          setChatState(prev => ({ ...prev, isPaused: true }))
        } else if (data.type === 'chat_cancelled') {
          setMessages(prev => [...prev, { sender: 'bot', text: data.message || 'Собеседование отменено' }])
          setChatState(prev => ({ ...prev, isCompleted: true }))
        } else if (data.type === 'disconnected') {
          setMessages(prev => [...prev, { sender: 'bot', text: data.message || 'Соединение разорвано' }])
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }
    ws.onclose = () => {
      setMessages(prev => [...prev, { sender: 'bot', text: 'Соединение закрыто.' }])
      scheduleReconnect()
    }
    ws.onerror = () => {
      try { ws.close() } catch {}
    }
  }

  const [input, setInput] = useState('')
  const sendMsg = () => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const text = input.trim()
    if (!text) return
    ws.send(JSON.stringify({ message: text }))
    setMessages(prev => [...prev, { sender: 'me', text }])
    setInput('')
  }

  useEffect(() => {
    return () => {
      if (reconnectTimer.current) window.clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [])

  return (
    <>
      <div className="mx-auto max-w-3xl px-4 py-6 space-y-6">
        <section className="bg-white rounded-lg shadow p-4 space-y-3">
          <h2 className="text-lg font-semibold">Candidate</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className={inputCls} placeholder="Full name" value={fullName} onChange={e => setFullName(e.target.value)} />
          <input className={inputCls} placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input className={inputCls} placeholder="Phone" value={phone} onChange={e => setPhone(e.target.value)} />
          <input className={inputCls} placeholder="City" value={city} onChange={e => setCity(e.target.value)} />
          <textarea className={`${inputCls} min-h-24 md:col-span-2`} placeholder="Resume text" value={resumeText} onChange={e => setResumeText(e.target.value)} />
        </div>
        <div className="space-x-2">
          <button className={btnCls} onClick={createCandidate}>Create Candidate</button>
          {candidateId && <span className="text-sm text-gray-600">Candidate ID: {candidateId}</span>}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow p-4 space-y-3">
        <h2 className="text-lg font-semibold">Response</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className={inputCls} placeholder="Vacancy ID" value={vacancyId} onChange={e => setVacancyId(e.target.value)} />
        </div>
        <div className="space-x-2">
          <button className={btnCls} onClick={createResponse} disabled={!candidateId || !vacancyId}>Create Response</button>
          {responseId && <span className="text-sm text-gray-600">Response ID: {responseId}</span>}
        </div>
      </section>
      
      {/* Floating Chat Button for Candidate */}
      {responseId && (
        <div className="fixed bottom-6 right-6 z-40">
          <button
            onClick={() => setShowPreChat(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-2xl flex items-center gap-3 transition-all hover:scale-105 animate-bounce"
            style={{ animationDuration: '2s' }}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <span className="font-medium">Пройти мини-собеседование (~2 мин)</span>
          </button>
        </div>
      )}

      {/* Chat Modal */}
      <ChatModal
        isOpen={showChatModal}
        onClose={handleModalClose}
        messages={messages}
        chatState={chatState}
        input={input}
        setInput={setInput}
        onSendMessage={sendMsg}
        onKeyPress={(e) => e.key === 'Enter' ? sendMsg() : undefined}
        onPause={handlePauseChat}
        onCancel={handleCancelChat}
      />

        {/* Pre-chat Screen */}
        <PreChatScreen
          isOpen={showPreChat}
          onStart={handlePreChatStart}
          onCancel={handlePreChatCancel}
        />
      </div>
    </>
  )
}
