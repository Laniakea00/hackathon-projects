import { useEffect, useMemo, useState, useRef } from 'react'
import { api, wsUrl } from '../lib/api'

type Vacancy = {
  id: string
  title: string
  description: string
  requirements?: { stack?: string[] }
  location: string
  salary_min?: number | null
  salary_max?: number | null
  created_at?: string
}

export default function Catalog() {
  // Data
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [selectedVacancyId, setSelectedVacancyId] = useState<string>('')

  // Candidate (client-side state)
  const [candidateId, setCandidateId] = useState<string | null>(() => {
    try { return localStorage.getItem('candidate_id') } catch { return null }
  })
  const [fullName, setFullName] = useState<string>(() => {
    try { return localStorage.getItem('candidate_name') || '' } catch { return '' }
  })
  const [email, setEmail] = useState<string>(() => {
    try { return localStorage.getItem('candidate_email') || '' } catch { return '' }
  })
  const [city, setCity] = useState<string>(() => {
    try { return localStorage.getItem('candidate_city') || '' } catch { return '' }
  })
  const [resumeSnippet, setResumeSnippet] = useState<string>(() => {
    try { return localStorage.getItem('candidate_resume_snippet') || '' } catch { return '' }
  })

  // Upload & apply
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string>('')
  const [err, setErr] = useState<string>('')
  
  // Chat state
  const [responseId, setResponseId] = useState<string | null>(null)
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
  const [input, setInput] = useState('')
  const wsRef = useRef<WebSocket | null>(null)

  // Search UI
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState<'new' | 'top' | 'almaty'>('new')
  const [showResumeEditor, setShowResumeEditor] = useState(false)

  // Load vacancies
  useEffect(() => {
    api.get('/vacancies').then(r => setVacancies(r.data)).catch(() => setVacancies([]))
  }, [])

  useEffect(() => {
    if (!selectedVacancyId && vacancies.length) setSelectedVacancyId(vacancies[0].id)
  }, [vacancies, selectedVacancyId])

  // Check if candidate already applied to selected vacancy
  useEffect(() => {
    if (!selectedVacancyId || !candidateId) {
      setResponseId(null)
      return
    }
    
    // Try to get existing response for this vacancy
    api.get(`/responses/candidate/${candidateId}/vacancy/${selectedVacancyId}`)
      .then(r => {
        if (r.data && r.data.id) {
          setResponseId(r.data.id)
          // Store response_id with vacancy_id as key
          try { 
            localStorage.setItem(`response_${candidateId}_${selectedVacancyId}`, r.data.id)
            console.log('Found existing response:', r.data.id)
          } catch {}
        } else {
          setResponseId(null)
        }
      })
      .catch((err) => {
        // 404 means no response exists for this vacancy
        if (err.response?.status === 404) {
          setResponseId(null)
        } else {
          // For other errors, try to load from localStorage
          try {
            const stored = localStorage.getItem(`response_${candidateId}_${selectedVacancyId}`)
            if (stored) {
              setResponseId(stored)
              console.log('Loaded response from localStorage:', stored)
            } else {
              setResponseId(null)
            }
          } catch {
            setResponseId(null)
          }
        }
      })
  }, [selectedVacancyId, candidateId])

  const filtered = useMemo(() => {
    let list = vacancies
    if (tab === 'almaty') list = list.filter(v => (v.location || '').toLowerCase().includes('алматы') || (v.location || '').toLowerCase().includes('almaty'))
    if (tab === 'top') list = list.slice().sort((a, b) => (b.salary_max || 0) - (a.salary_max || 0))
    if (query.trim()) {
      const q = query.toLowerCase()
      list = list.filter(v => [v.title, v.location, (v.requirements?.stack || []).join(' ')].some(t => (t || '').toLowerCase().includes(q)))
    }
    return list
  }, [vacancies, tab, query])

  const selectedVacancy = filtered.find(v => v.id === selectedVacancyId) || filtered[0]

  // Upload PDF -> create candidate and store id
  const uploadResume = async () => {
    if (!pdfFile) {
      setErr('Выберите PDF‑файл')
      return
    }
    if (!fullName || !email) {
      setErr('Заполните ФИО и E‑mail')
      return
    }
    setBusy(true); setErr(''); setMsg('')
    try {
      const form = new FormData()
      form.append('file', pdfFile)
      form.append('full_name', fullName)
      form.append('email', email)
      form.append('city', city)
      const res = await api.post('/candidates/upload_pdf', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      const id = res.data.id as string
      setCandidateId(id)
      try {
        localStorage.setItem('candidate_id', id)
        localStorage.setItem('candidate_name', fullName)
        localStorage.setItem('candidate_email', email)
        localStorage.setItem('candidate_city', city)
        const snippet = (res.data.resume_text || '').slice(0, 400)
        localStorage.setItem('candidate_resume_snippet', snippet)
        setResumeSnippet(snippet)
      } catch {}
      setMsg('Резюме загружено и сохранено')
    } catch (e: any) {
      setErr('Не удалось загрузить PDF. Попробуйте ещё раз.')
    } finally {
      setBusy(false)
    }
  }

  // Chat functions
  const handlePreChatStart = (language: string, consent: boolean) => {
    setShowPreChat(false)
    setShowChatModal(true)
    connectWs()
  }

  const handlePreChatCancel = () => {
    setShowPreChat(false)
  }

  const handleModalClose = () => {
    // Just hide modal - don't close WebSocket or clear state
    // This allows user to resume the chat later
    setShowChatModal(false)
    // WebSocket stays open, messages and state persist
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
      setMessages(prev => [...prev, { sender: 'bot', text: 'Соединение установлено. Ожидание вопросов...' }])
    }
    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'bot_message' && data.message) {
          // Use typewriter effect for bot messages
          await typeBotMessage(data.message)
          const remaining = (data.total_questions || 0) - (data.question_index || 0) - 1
          const estimatedMinutes = Math.max(1, Math.ceil((remaining * 30) / 60))
          setChatState(prev => ({
            ...prev,
            questionIndex: data.question_index || prev.questionIndex,
            totalQuestions: data.total_questions || prev.totalQuestions,
            currentScore: data.current_score || prev.currentScore,
            estimatedTimeMinutes: estimatedMinutes,
            isCompleted: false
          }))
        } else if (data.type === 'chat_ended') {
          setChatState(prev => ({
            ...prev,
            isCompleted: true,
            verdict: data.verdict || prev.verdict,
            finalScore: data.final_score || prev.finalScore
          }))
        } else if (data.type === 'chat_paused') {
          await typeBotMessage(data.message || 'Собеседование приостановлено. Вы можете продолжить в любое время.')
          setChatState(prev => ({ ...prev, isPaused: true }))
        } else if (data.type === 'chat_cancelled') {
          await typeBotMessage(data.message || 'Собеседование отменено.')
          setChatState(prev => ({ ...prev, isCompleted: true }))
        } else if (data.type === 'disconnected') {
          setMessages(prev => [...prev, { sender: 'bot', text: data.message || 'Соединение разорвано' }])
        } else if (data.type === 'hr_decision') {
          // HR made a decision (approve/reject) - show message with typewriter effect
          await typeBotMessage(data.message)
        } else if (data.type === 'hr_decision_update') {
          // HR updated their decision - show update message with typewriter effect
          await typeBotMessage(data.message)
        } else if (data.type === 'info') {
          // Info message from backend
          await typeBotMessage(data.message)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }
    ws.onclose = () => {
      setMessages(prev => [...prev, { sender: 'bot', text: 'Соединение закрыто.' }])
    }
    ws.onerror = () => {
      try { ws.close() } catch {}
    }
  }

  // Typewriter effect for bot messages (like ChatGPT)
  const typeBotMessage = async (text: string) => {
    let insertIndex = -1
    setMessages(prev => {
      insertIndex = prev.length
      return [...prev, { sender: 'bot' as const, text: '' }]
    })
    
    const speed = 15 // milliseconds per character
    for (let i = 1; i <= text.length; i++) {
      await new Promise(res => setTimeout(res, speed))
      const slice = text.slice(0, i)
      setMessages(prev => {
        const arr = [...prev]
        if (arr[insertIndex]) {
          arr[insertIndex] = { sender: 'bot' as const, text: slice }
        }
        return arr
      })
    }
  }

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
      wsRef.current?.close()
    }
  }, [])

  // Apply with existing candidateId, or create lightweight profile
  const apply = async () => {
    if (!selectedVacancy) return
    setBusy(true); setErr(''); setMsg('')
    try {
      let cid = candidateId
      if (!cid) {
        if (!fullName || !email) {
          setErr('Укажите ФИО и E‑mail или загрузите резюме PDF')
          setBusy(false)
          return
        }
        const c = await api.post('/candidates', { full_name: fullName, email, city: city || '—', resume_text: resumeSnippet || '' })
        cid = c.data.id
        setCandidateId(cid)
        try { localStorage.setItem('candidate_id', cid as string) } catch {}
      }
      const response = await api.post('/responses', { candidate_id: cid, vacancy_id: selectedVacancy.id })
      setResponseId(response.data.id)
      // Store response_id with vacancy_id as key
      try { 
        localStorage.setItem(`response_${cid}_${selectedVacancy.id}`, response.data.id)
        console.log('Saved new response to localStorage:', response.data.id)
      } catch {}
      setMsg('Спасибо! Отклик отправлен. Теперь вы можете пройти мини-собеседование.')
    } catch (e: any) {
      setErr('Не удалось отправить отклик. Попробуйте ещё раз.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      {/* Filters */}
      {/* Filter bar (static, not sticky) */}
      <section className="bg-white border-b border-[#E6E8EB]">
        <div className="container py-4">
          <div className="w-full flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 border border-[#E6E8EB] rounded-xl px-3 py-2">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M21 21l-4.3-4.3" stroke="#98A2B3" strokeWidth="2" strokeLinecap="round"/><circle cx="11" cy="11" r="7" stroke="#98A2B3" strokeWidth="2"/></svg>
                <input className="flex-1 outline-none" aria-label="Поиск" placeholder="Поиск по вакансии, навыкам, городу" value={query} onChange={e => setQuery(e.target.value)} />
                <button className="btn-primary">Найти</button>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className={`tab ${tab === 'new' ? 'active' : ''}`} onClick={() => setTab('new')}>Новые вакансии</button>
              <button className={`tab ${tab === 'top' ? 'active' : ''}`} onClick={() => setTab('top')}>Топ зарплаты</button>
              <button className={`tab ${tab === 'almaty' ? 'active' : ''}`} onClick={() => setTab('almaty')}>Работа в Алматы</button>
            </div>
          </div>
        </div>
      </section>

      {/* Grid */}
      <div className="container py-6">
        <div className="grid-cols-preview">
          {/* Left: vacancies list */}
          <div className="space-y-3">
            {filtered.map(v => (
              <div key={v.id} className={`card p-4 hover:border-primary-600 ${selectedVacancy?.id === v.id ? 'border-primary-600' : ''}`} onClick={() => setSelectedVacancyId(v.id)} role="button" aria-label={`Открыть вакансию ${v.title}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-[18px] leading-[24px] font-semibold text-grayx-900">{v.title}</div>
                    <div className="text-[14px] leading-[20px] text-grayx-600">{v.location}</div>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className="badge">{[v.salary_min, v.salary_max].filter(Boolean).join(' — ') || 'З/п не указана'}</span>
                  {(v.requirements?.stack || []).slice(0, 4).map((s, i) => (<span key={i} className="badge">{s}</span>))}
                </div>
                <div className="mt-3 flex items-center justify-between text-[12px] leading-[18px] text-grayx-600">
                  <span>Опубликовано {formatDays(v.created_at)} назад</span>
                  <a className="link" href="#">ПРЕДПРОСМОТР</a>
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="text-sm text-grayx-600">Нет вакансий по вашему запросу</div>
            )}
          </div>

          {/* Right: resume + apply */}
          <div className="space-y-4 sticky" style={{ top: 16 }}>
            {/* My Resume (collapsed by default) */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-[16px] font-semibold text-grayx-900">Моё резюме</h3>
                {!showResumeEditor && !candidateId && (
                  <button className="btn-outline" onClick={() => setShowResumeEditor(true)}>Заполнить</button>
                )}
              </div>
              {!candidateId && !showResumeEditor && (
                <div className="text-[12px] text-[#666]">Добавьте резюме позже или загрузите PDF — форма спрятана, чтобы не мешать.</div>
              )}
              {(!candidateId && showResumeEditor) && (
                <div className="space-y-2">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <input className="border rounded px-3 py-2" placeholder="ФИО" value={fullName} onChange={e => setFullName(e.target.value)} />
                    <input className="border rounded px-3 py-2" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
                    <input className="border rounded px-3 py-2" placeholder="Город" value={city} onChange={e => setCity(e.target.value)} />
                    <input className="border rounded px-3 py-2" type="file" accept="application/pdf" onChange={e => setPdfFile(e.target.files?.[0] || null)} />
                  </div>
                  <div className="mt-1 flex gap-2">
                    <button className="btn-primary" onClick={uploadResume} disabled={busy}>Загрузить PDF</button>
                    <button className="btn-outline" onClick={() => { setPdfFile(null); setResumeSnippet(''); setCandidateId(null); try { localStorage.removeItem('candidate_id'); localStorage.removeItem('candidate_resume_snippet') } catch {} }}>Очистить</button>
                    <button className="btn-outline" onClick={() => setShowResumeEditor(false)}>Скрыть</button>
                  </div>
                </div>
              )}
              {candidateId && (
                <div className="text-[12px] text-grayx-600">Резюме загружено. ID: {candidateId}</div>
              )}
              {resumeSnippet && (
                <div className="mt-3 text-[12px] text-grayx-600 max-h-40 overflow-auto border rounded p-2 bg-grayx-50">{resumeSnippet}</div>
              )}
            </div>

            {/* Apply */}
            <div className="card p-4">
              <h3 className="text-[16px] font-semibold text-grayx-900 mb-2">Отклик на вакансию</h3>
              <div className="text-[12px] text-grayx-600 mb-2">Вакансия: <b>{selectedVacancy?.title || '—'}</b> ({selectedVacancy?.location || '—'})</div>
              
              {/* Show status if user has applied */}
              {responseId && (
                <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded">
                  <div className="text-xs text-blue-800 font-medium">Статус отклика:</div>
                  <div className="text-sm text-blue-900 mt-1">
                    {chatState.isCompleted && chatState.verdict === 'подходит' && '✅ Одобрено'}
                    {chatState.isCompleted && chatState.verdict !== 'подходит' && '⏳ На рассмотрении'}
                    {!chatState.isCompleted && messages.length > 0 && '💬 Собеседование в процессе'}
                    {!chatState.isCompleted && messages.length === 0 && '📝 Ожидает собеседования'}
                  </div>
                </div>
              )}
              
              <div className="flex gap-2 flex-wrap">
                <button className="btn-primary" onClick={apply} disabled={busy || !selectedVacancy || !!responseId}>
                  {responseId ? 'Уже откликнулись' : 'Откликнуться'}
                </button>
                <button className="btn-outline" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>К списку</button>
                
                {/* Chat button - show if user has applied */}
                {responseId && (
                  <button 
                    className="btn-primary bg-green-600 hover:bg-green-700" 
                    onClick={() => {
                      if (messages.length > 0) {
                        setShowChatModal(true)
                      } else {
                        setShowPreChat(true)
                      }
                    }}
                  >
                    💬 {messages.length > 0 ? 'Продолжить чат' : 'Открыть чат'}
                  </button>
                )}
              </div>
              {msg && <div className="text-sm text-success-600 mt-2">{msg}</div>}
              {err && <div className="text-sm text-danger-600 mt-2">{err}</div>}
            </div>
          </div>
        </div>
      </div>

      {/* Floating Chat Button */}
      {responseId && !showChatModal && (
        <div className="fixed bottom-6 right-6 z-50">
          <button
            onClick={() => {
              // If chat already started, resume it directly
              if (messages.length > 0) {
                setShowChatModal(true)
              } else {
                setShowPreChat(true)
              }
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-2xl flex items-center gap-3 transition-all hover:scale-105 animate-bounce"
            style={{ animationDuration: '2s' }}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <span className="font-medium">
              {messages.length > 0 ? 'Продолжить собеседование' : 'Пройти мини-собеседование (~2 мин)'}
            </span>
          </button>
        </div>
      )}

      {/* Pre-chat Screen */}
      {showPreChat && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-semibold mb-4">Пройти мини-собеседование</h2>
            <div className="mb-6">
              <p className="text-gray-600 mb-4">
                Перед началом собеседования выберите язык и подтвердите согласие на обработку данных.
              </p>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Выберите язык</label>
                <select className="w-full border rounded px-3 py-2">
                  <option value="ru">Русский</option>
                  <option value="kk">Қазақша</option>
                  <option value="en">English</option>
                </select>
              </div>
              <div className="mb-4">
                <label className="flex items-start">
                  <input type="checkbox" className="mt-1 mr-2" />
                  <span className="text-sm text-gray-700">
                    Я согласен на обработку моих данных в соответствии с политикой конфиденциальности
                  </span>
                </label>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => handlePreChatStart('ru', true)}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
              >
                Начать (~2 мин)
              </button>
              <button
                onClick={handlePreChatCancel}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Chat Modal */}
      {showChatModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg w-full max-w-4xl h-[80vh] flex flex-col m-4">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-semibold">Мини-собеседование</h2>
              <button
                onClick={handleModalClose}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                ×
              </button>
            </div>

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
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(chatState.questionIndex / chatState.totalQuestions) * 100}%` }}
                  ></div>
                </div>
                {!chatState.isPaused && (
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={handlePauseChat}
                      className="text-sm px-3 py-1 text-gray-600 hover:text-gray-800"
                    >
                      ⏸ Приостановить
                    </button>
                    <button
                      onClick={handleCancelChat}
                      className="text-sm px-3 py-1 text-red-600 hover:text-red-800"
                    >
                      ✕ Отменить
                    </button>
                  </div>
                )}
              </div>
            )}

            {chatState.isCompleted && (
              <div className="bg-blue-50 p-4 border-b border-blue-200">
                <div className="flex items-center gap-3">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <h3 className="font-medium text-gray-900">Спасибо за ваши ответы!</h3>
                    <p className="text-sm text-gray-600">Мы получили вашу информацию и свяжемся с вами в ближайшее время.</p>
                  </div>
                </div>
              </div>
            )}

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
            </div>

            <div className="p-4 border-t">
              <div className="flex gap-2">
                <input
                  className="flex-1 border rounded px-3 py-2"
                  placeholder={chatState.isCompleted ? "Собеседование завершено" : "Введите ваш ответ..."}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' ? sendMsg() : undefined}
                  disabled={chatState.isCompleted}
                />
                <button
                  onClick={sendMsg}
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
      )}
    </div>
  )
}

function formatDays(created?: string) {
  if (!created) return 'недавно'
  try {
    const d = new Date(created)
    const diff = Math.max(0, Date.now() - d.getTime())
    const days = Math.floor(diff / (24 * 60 * 60 * 1000))
    return days === 0 ? 'сегодня' : `${days} дн.`
  } catch {
    return 'недавно'
  }
}

