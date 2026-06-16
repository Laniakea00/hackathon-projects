import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import InterviewSummary from '../components/InterviewSummary'
import ChatHistory from '../components/ChatHistory'

export default function EmployerDashboard() {
  const [token, setToken] = useState<string | null>(null)
  const authHeaders = useMemo(() => token ? { Authorization: `Bearer ${token}` } : {}, [token])

  // Register/Login
  const [companyName, setCompanyName] = useState('Test Corp')
  const [email, setEmail] = useState('hr@test.com')
  const [password, setPassword] = useState('test1234')
  const [authMsg, setAuthMsg] = useState('')

  // Create vacancy
  const [title, setTitle] = useState('Python Developer')
  const [description, setDescription] = useState('We need a FastAPI developer')
  const [location, setLocation] = useState('Moscow')
  const [salaryMin, setSalaryMin] = useState<number | ''>(100000)
  const [salaryMax, setSalaryMax] = useState<number | ''>(200000)
  const [vacancyId, setVacancyId] = useState<string>('')

  // Responses
  const [responses, setResponses] = useState<any[]>([])
  const [selectedResponseId, setSelectedResponseId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'summary' | 'chat'>('summary')

  // AI Mismatch quick test
  const [jobText, setJobText] = useState('Python backend developer, FastAPI, PostgreSQL, Docker, office in Almaty, EN B2')
  const [cvText, setCvText] = useState('Python dev 1 year, Flask, SQLite, remote from Astana, English B1')
  const [mismatchResult, setMismatchResult] = useState<any | null>(null)

  // AI Pipeline state
  const [pipelineResult, setPipelineResult] = useState<any | null>(null)
  const [pipelineLoading, setPipelineLoading] = useState(false)
  const [candidateIdForScreen, setCandidateIdForScreen] = useState('')
  const [responseIdForScreen, setResponseIdForScreen] = useState('')

  const inputCls = 'border rounded px-3 py-2 w-full'
  const btnCls = 'inline-flex items-center gap-2 rounded bg-blue-600 text-white px-3 py-2 text-sm hover:bg-blue-700 disabled:opacity-50'

  const register = async () => {
    setAuthMsg('')
    const res = await api.post(`/employers/register`, { company_name: companyName, email, password })
    setToken(res.data.access_token)
    setAuthMsg('Registered and logged in')
  }

  const login = async () => {
    setAuthMsg('')
    const res = await api.post(`/auth/login`, { email, password })
    setToken(res.data.access_token)
    setAuthMsg('Logged in')
  }

  const createVacancy = async () => {
    const res = await api.post(`/vacancies`, {
      title,
      description,
      location,
      salary_min: salaryMin === '' ? null : salaryMin,
      salary_max: salaryMax === '' ? null : salaryMax,
      requirements: { stack: ['python', 'fastapi'] },
    }, { headers: authHeaders })
    setVacancyId(res.data.id)
  }

  const loadResponses = async () => {
    const url = vacancyId ? `/responses?vacancy_id=${vacancyId}` : `/responses`
    const res = await api.get(url, { headers: authHeaders })
    console.log('Loaded responses:', res.data)
    setResponses(res.data)
  }

  const runMismatch = async () => {
    const res = await api.post(`/ai/mismatch`, {
      job_text: jobText,
      cv_text: cvText,
      hints: {
        must_have_skills: ['python', 'fastapi', 'postgresql'],
        lang_requirement: 'EN B2',
        location_requirement: 'Almaty, office 3/5',
        salary_range: { min: 600000, max: 900000, currency: 'KZT' },
      },
    })
    setMismatchResult(res.data)
  }

  const runPipelineWithTexts = async () => {
    setPipelineLoading(true)
    try {
      const res = await api.post(`/ai/pipeline/screen`, {
        job_text: jobText,
        cv_text: cvText,
        limits: { max_questions: 3 },
        hints: {
          must_have_skills: ['python', 'fastapi', 'postgresql']
        }
      })
      setPipelineResult(res.data)
    } finally {
      setPipelineLoading(false)
    }
  }

  const runPipelineByIds = async () => {
    if (!vacancyId || !candidateIdForScreen) return
    setPipelineLoading(true)
    try {
      const res = await api.post(`/ai/pipeline/screen_by_ids`, {
        vacancy_id: vacancyId,
        candidate_id: candidateIdForScreen,
        response_id: responseIdForScreen || null,
        limits: { max_questions: 3 }
      }, { headers: authHeaders })
      setPipelineResult(res.data)
    } finally {
      setPipelineLoading(false)
    }
  }

  useEffect(() => {
    if (token && vacancyId) {
      loadResponses().catch(() => {})
    }
  }, [token, vacancyId])

  const ScoreCard = ({ scorer }: { scorer: any }) => {
    if (!scorer) return null
    const s = scorer.scores_pct || {}
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
        <div className="p-2 border rounded">Overall: <b>{scorer.overall_match_pct}%</b> — {scorer.verdict}</div>
        <div className="p-2 border rounded">Exp: {s.experience}%</div>
        <div className="p-2 border rounded">Skills: {s.skills}%</div>
        <div className="p-2 border rounded">Langs: {s.langs}%</div>
        <div className="p-2 border rounded">Edu: {s.education}%</div>
        <div className="p-2 border rounded">Location: {s.location}%</div>
        <div className="p-2 border rounded">Domain: {s.domain}%</div>
        <div className="p-2 border rounded">Comp: {s.comp}%</div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 space-y-8">
      {/* DEBUG BANNER - REMOVE AFTER TESTING */}
      <div className="bg-red-600 text-white p-4 rounded-lg text-center font-bold text-xl">
        🔴 DEBUG MODE ACTIVE - VERSION 2.0 - BUTTONS SHOULD BE VISIBLE 🔴
      </div>
      
      <section className="bg-white rounded-lg shadow p-4 space-y-3">
        <h2 className="text-lg font-semibold">Auth</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input className={inputCls} placeholder="Company" value={companyName} onChange={e => setCompanyName(e.target.value)} />
          <input className={inputCls} placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input className={inputCls} placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} />
        </div>
        <div className="space-x-2">
          <button className={btnCls} onClick={register}>Register</button>
          <button className={btnCls} onClick={login}>Login</button>
          {authMsg && <span className="text-sm text-green-600 ml-2">{authMsg}</span>}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow p-4 space-y-3">
        <h2 className="text-lg font-semibold">Create Vacancy</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className={inputCls} placeholder="Title" value={title} onChange={e => setTitle(e.target.value)} />
          <input className={inputCls} placeholder="Location" value={location} onChange={e => setLocation(e.target.value)} />
          <textarea className={`${inputCls} min-h-24`} placeholder="Description" value={description} onChange={e => setDescription(e.target.value)} />
          <div className="flex gap-2">
            <input className={inputCls} type="number" placeholder="Salary min" value={salaryMin} onChange={e => setSalaryMin(e.target.value === '' ? '' : Number(e.target.value))} />
            <input className={inputCls} type="number" placeholder="Salary max" value={salaryMax} onChange={e => setSalaryMax(e.target.value === '' ? '' : Number(e.target.value))} />
          </div>
        </div>
        <div className="space-x-2">
          <button className={btnCls} onClick={createVacancy} disabled={!token}>Create</button>
          {vacancyId && <span className="text-sm text-gray-600">Vacancy ID: {vacancyId}</span>}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow p-4 space-y-3">
        <h2 className="text-lg font-semibold">Responses</h2>
        <div className="space-x-2">
          <button className={btnCls} onClick={loadResponses} disabled={!token}>Load Responses</button>
        </div>
        <div className="mt-3 divide-y">
          {responses.map((r) => (
            <div key={r.id} className="py-3 hover:bg-gray-50 transition rounded px-2">
              <div className="font-medium">{r.candidate_name} — {r.candidate_email} — {r.candidate_city}</div>
              <div className="text-sm text-gray-600 mb-2">
                status: <span className={`font-semibold ${
                  r.status === 'approved' ? 'text-green-600' :
                  r.status === 'rejected' ? 'text-red-600' :
                  r.status === 'in_chat' ? 'text-blue-600' :
                  'text-gray-600'
                }`}>{r.status}</span> | score: {r.relevance_score ? `${Math.round(r.relevance_score * 100)}%` : 'n/a'}
              </div>
              {r.rejection_reasons && <pre className="text-xs mt-1 bg-gray-50 p-2 rounded border">{JSON.stringify(r.rejection_reasons, null, 2)}</pre>}
              
              <div className="flex flex-wrap gap-2 mt-3">
                <button
                  className="text-sm px-3 py-1.5 bg-blue-100 text-blue-700 hover:bg-blue-200 rounded flex items-center gap-2 transition"
                  onClick={(e) => {
                    e.stopPropagation()
                    setViewMode('summary')
                    setSelectedResponseId(r.id)
                  }}
                >
                  📊 Просмотреть сводку
                </button>
                
                <button
                  className="text-sm px-3 py-1.5 bg-purple-100 text-purple-700 hover:bg-purple-200 rounded flex items-center gap-2 transition"
                  onClick={(e) => {
                    e.stopPropagation()
                    setViewMode('chat')
                    setSelectedResponseId(r.id)
                  }}
                >
                  💬 История чата
                </button>
                
                {/* Debug: show current status */}
                <div className="text-xs px-2 py-1 bg-gray-100 rounded">
                  Status: "{r.status}"
                </div>
                
                {/* Show decision result if already approved/rejected */}
                {r.status === 'approved' && (
                  <div className="text-sm px-3 py-1.5 bg-green-100 text-green-800 rounded flex items-center gap-2 font-semibold">
                    ✅ Одобрен
                  </div>
                )}
                
                {r.status === 'rejected' && (
                  <div className="text-sm px-3 py-1.5 bg-red-100 text-red-800 rounded flex items-center gap-2 font-semibold">
                    ❌ Отклонён
                  </div>
                )}
                
                {/* Approve/Reject buttons - ALWAYS SHOW FOR DEBUG */}
                <button
                  className="text-sm px-3 py-1.5 bg-green-100 text-green-700 hover:bg-green-200 rounded flex items-center gap-2 transition font-medium"
                  onClick={async (e) => {
                    e.stopPropagation()
                    if (confirm(`Одобрить кандидата ${r.candidate_name}?`)) {
                      try {
                        await api.post(`/responses/${r.id}/approve`, {}, { headers: authHeaders })
                        alert('Кандидат одобрен! Уведомление отправлено.')
                        await loadResponses()
                      } catch (err) {
                        console.error('Approve error:', err)
                        alert('Ошибка при одобрении')
                      }
                    }
                  }}
                >
                  ✅ Одобрить
                </button>
                
                <button
                  className="text-sm px-3 py-1.5 bg-red-100 text-red-700 hover:bg-red-200 rounded flex items-center gap-2 transition font-medium"
                  onClick={async (e) => {
                    e.stopPropagation()
                    if (confirm(`Отклонить кандидата ${r.candidate_name}?`)) {
                      try {
                        await api.post(`/responses/${r.id}/reject`, {}, { headers: authHeaders })
                        alert('Кандидат отклонён. Вежливое уведомление отправлено.')
                        await loadResponses()
                      } catch (err) {
                        console.error('Reject error:', err)
                        alert('Ошибка при отклонении')
                      }
                    }
                  }}
                >
                  ❌ Отклонить
                </button>
              </div>
            </div>
          ))}
          {responses.length === 0 && <div className="text-sm text-gray-500">No responses yet</div>}
        </div>
      </section>

      {/* Summary/Chat Modal */}
      {selectedResponseId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-auto">
          <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-auto relative">
            <div className="sticky top-0 z-10 bg-white border-b flex items-center justify-between p-4">
              <div className="flex gap-2">
                <button
                  onClick={() => setViewMode('summary')}
                  className={`px-4 py-2 rounded ${
                    viewMode === 'summary' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  📊 Сводка
                </button>
                <button
                  onClick={() => setViewMode('chat')}
                  className={`px-4 py-2 rounded ${
                    viewMode === 'chat' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  💬 История чата
                </button>
              </div>
              <button
                onClick={() => setSelectedResponseId(null)}
                className="text-gray-400 hover:text-gray-600 text-2xl bg-white rounded-full w-8 h-8 flex items-center justify-center"
              >
                ×
              </button>
            </div>
            <div className="p-4">
              {viewMode === 'summary' ? (
                <InterviewSummary responseId={selectedResponseId} />
              ) : (
                <ChatHistory responseId={selectedResponseId} />
              )}
            </div>
          </div>
        </div>
      )}

      <section className="bg-white rounded-lg shadow p-4 space-y-3">
        <h2 className="text-lg font-semibold">AI: End-to-End Screening</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <h3 className="font-medium">By Texts</h3>
            <textarea className={`${inputCls} min-h-32`} placeholder="Job text (JD)" value={jobText} onChange={e => setJobText(e.target.value)} />
            <textarea className={`${inputCls} min-h-32`} placeholder="CV text" value={cvText} onChange={e => setCvText(e.target.value)} />
            <button className={btnCls} onClick={runPipelineWithTexts} disabled={pipelineLoading}>Run Pipeline</button>
          </div>
          <div className="space-y-2">
            <h3 className="font-medium">By IDs</h3>
            <input className={inputCls} placeholder="Candidate ID" value={candidateIdForScreen} onChange={e => setCandidateIdForScreen(e.target.value)} />
            <input className={inputCls} placeholder="Response ID (optional)" value={responseIdForScreen} onChange={e => setResponseIdForScreen(e.target.value)} />
            <button className={btnCls} onClick={runPipelineByIds} disabled={!vacancyId || !candidateIdForScreen || pipelineLoading}>Run by IDs (persist)</button>
          </div>
        </div>
        {pipelineResult && (
          <div className="mt-4 space-y-3">
            <ScoreCard scorer={pipelineResult.scorer} />
            <details className="border rounded p-2">
              <summary className="cursor-pointer">Mismatch</summary>
              <pre className="text-xs bg-gray-50 p-2 rounded border overflow-auto max-h-80">{JSON.stringify(pipelineResult.mismatch, null, 2)}</pre>
            </details>
            <details className="border rounded p-2">
              <summary className="cursor-pointer">Clarifier</summary>
              <pre className="text-xs bg-gray-50 p-2 rounded border overflow-auto max-h-80">{JSON.stringify(pipelineResult.clarifier, null, 2)}</pre>
            </details>
            <details className="border rounded p-2">
              <summary className="cursor-pointer">Orchestrator (summary)</summary>
              <pre className="text-xs bg-gray-50 p-2 rounded border overflow-auto max-h-80">{JSON.stringify(pipelineResult.orchestrator, null, 2)}</pre>
            </details>
            <details className="border rounded p-2">
              <summary className="cursor-pointer">Scorer</summary>
              <pre className="text-xs bg-gray-50 p-2 rounded border overflow-auto max-h-80">{JSON.stringify(pipelineResult.scorer, null, 2)}</pre>
            </details>
          </div>
        )}
      </section>

      <section className="bg-white rounded-lg shadow p-4 space-y-3">
        <h2 className="text-lg font-semibold">AI: Mismatch Detector (test)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <textarea className={`${inputCls} min-h-40`} placeholder="Job text (JD)" value={jobText} onChange={e => setJobText(e.target.value)} />
          <textarea className={`${inputCls} min-h-40`} placeholder="CV text" value={cvText} onChange={e => setCvText(e.target.value)} />
        </div>
        <div className="space-x-2">
          <button className={btnCls} onClick={runMismatch}>Run Mismatch</button>
        </div>
        {mismatchResult && (
          <pre className="text-xs mt-3 bg-gray-50 p-2 rounded border overflow-auto max-h-96">{JSON.stringify(mismatchResult, null, 2)}</pre>
        )}
      </section>
    </div>
  )
}
