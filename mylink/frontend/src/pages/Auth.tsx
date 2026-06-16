import { useState } from 'react'
import { api, persistAuthToken, setRole, getRole } from '../lib/api'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Auth() {
  const nav = useNavigate()
  const [tab, setTab] = useState<'employer' | 'candidate'>('employer')

  // If role already chosen, lock until logout
  useEffect(() => {
    const r = getRole()
    if (r === 'employer') nav('/employer-admin', { replace: true })
    if (r === 'candidate') nav('/', { replace: true })
  }, [])

  // Employer
  const [company, setCompany] = useState('MyLink HR')
  const [email, setEmail] = useState('hr@example.com')
  const [password, setPassword] = useState('test1234')
  const [msg, setMsg] = useState('')

  const registerEmployer = async () => {
    const r = await api.post('/employers/register', { company_name: company, email, password })
    persistAuthToken(r.data.access_token)
    setRole('employer')
    setMsg('Регистрация успешна. Токен сохранён.')
    nav('/employer-admin', { replace: true })
  }
  const loginEmployer = async () => {
    const r = await api.post('/auth/login', { email, password })
    persistAuthToken(r.data.access_token)
    setRole('employer')
    setMsg('Вход выполнен. Токен сохранён.')
    nav('/employer-admin', { replace: true })
  }

  // Candidate
  const [fullName, setFullName] = useState('Иван Иванов')
  const [cEmail, setCEmail] = useState('ivan@example.com')
  const [city, setCity] = useState('Алматы')
  const [cPassword, setCPassword] = useState('')
  // резюме вводится позже на отдельной странице

  const registerCandidate = async () => {
    const r = await api.post('/auth/candidate/register', { full_name: fullName, email: cEmail, city, password: cPassword || undefined })
    persistAuthToken(r.data.access_token)
    setRole('candidate')
    // Save candidate_id to localStorage
    if (r.data.candidate_id) {
      try {
        localStorage.setItem('candidate_id', r.data.candidate_id)
        localStorage.setItem('candidate_name', fullName)
        localStorage.setItem('candidate_email', cEmail)
        localStorage.setItem('candidate_city', city)
        console.log('Saved candidate_id to localStorage:', r.data.candidate_id)
      } catch {}
    }
    setMsg('Регистрация соискателя выполнена.')
    nav('/', { replace: true })
  }

  const loginCandidate = async () => {
    const r = await api.post('/auth/candidate/login', { email: cEmail, password: cPassword || undefined })
    persistAuthToken(r.data.access_token)
    setRole('candidate')
    // Save candidate_id to localStorage
    if (r.data.candidate_id) {
      try {
        localStorage.setItem('candidate_id', r.data.candidate_id)
        localStorage.setItem('candidate_email', cEmail)
        console.log('Saved candidate_id to localStorage:', r.data.candidate_id)
      } catch {}
    }
    setMsg('Вход выполнен.')
    nav('/', { replace: true })
  }

  return (
    <div className="relative min-h-[calc(100vh-64px-40px)] overflow-hidden">
      {/* Animated gradient background */}
      <div className="auth-bg" aria-hidden>
        <div className="auth-gradient" />
      </div>

      <div className="container animate-page min-h-[calc(100vh-64px-40px)] flex items-center py-8">
        <div className="mx-auto bg-white/80 backdrop-blur border border-[#E6E8EB] rounded-2xl shadow-sm overflow-hidden hover-lift" style={{ maxWidth: 960 }}>
          <div className="grid md:grid-cols-2">
            {/* Left: pitch */}
            <div className="hidden md:flex flex-col justify-center gap-4 p-8" style={{ background: 'linear-gradient(180deg,#F7F8FA 0%, #FFFFFF 100%)' }}>
              <div className="text-[28px] leading-[36px] font-semibold">Добро пожаловать в MyLink</div>
              <div className="text-[14px] text-[#666]">Ускорьте найм с помощью умных инструментов. Создайте аккаунт работодателя или начните как соискатель.</div>
              <div className="flex items-center gap-3 mt-2">
                <div className="w-24 h-10 rounded-lg bg-[#EEF2FF] shimmer" />
                <div className="w-16 h-10 rounded-lg bg-[#F1F3F5] shimmer" />
              </div>
            </div>
            {/* Right: form */}
            <div className="p-8">
              <div className="flex gap-2 mb-6" role="tablist">
                <button className={`px-5 py-2.5 rounded-xl border font-medium transition-colors hover-lift ${tab === 'employer' ? 'bg-[#2E6BFF] text-white border-[#2E6BFF]' : 'border-[#E6E8EB] text-[#0A0A0A] hover:bg-[#F7F8FA]'}`} onClick={() => setTab('employer')}>Работодатель</button>
                <button className={`px-5 py-2.5 rounded-xl border font-medium transition-colors hover-lift ${tab === 'candidate' ? 'bg-[#2E6BFF] text-white border-[#2E6BFF]' : 'border-[#E6E8EB] text-[#0A0A0A] hover:bg-[#F7F8FA]'}`} onClick={() => setTab('candidate')}>Соискатель</button>
              </div>

              {/* Reserve height to avoid layout jump */}
              <div style={{ minHeight: 280 }}>
                {tab === 'employer' && (
                  <section className="space-y-4 animate-up">
                    <div>
                      <label className="block text-[12px] text-[#666] mb-1">Компания</label>
                      <input className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#2E6BFF] outline-none" placeholder="Компания" value={company} onChange={e => setCompany(e.target.value)} />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[12px] text-[#666] mb-1">Email</label>
                        <input className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#2E6BFF] outline-none" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
                      </div>
                      <div>
                        <label className="block text-[12px] text-[#666] mb-1">Пароль</label>
                        <input className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#2E6BFF] outline-none" placeholder="Пароль" type="password" value={password} onChange={e => setPassword(e.target.value)} />
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button className="btn-primary hover-lift" onClick={registerEmployer}>Регистрация</button>
                      <button className="btn-outline hover-lift" onClick={loginEmployer}>Войти</button>
                    </div>
                    {msg && <div className="text-sm text-[#666]">{msg}</div>}
                  </section>
                )}

                {tab === 'candidate' && (
                  <section className="space-y-4 animate-up">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[12px] text-[#666] mb-1">ФИО</label>
                        <input className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#2E6BFF] outline-none" placeholder="ФИО" value={fullName} onChange={e => setFullName(e.target.value)} />
                      </div>
                      <div>
                        <label className="block text-[12px] text-[#666] mb-1">Email</label>
                        <input className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#2E6BFF] outline-none" placeholder="Email" value={cEmail} onChange={e => setCEmail(e.target.value)} />
                      </div>
                      <div>
                        <label className="block text-[12px] text-[#666] mb-1">Город</label>
                        <input className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#2E6BFF] outline-none" placeholder="Город" value={city} onChange={e => setCity(e.target.value)} />
                      </div>
                      <div>
                        <label className="block text-[12px] text-[#666] mb-1">Пароль</label>
                        <input className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#2E6BFF] outline-none" placeholder="Пароль" type="password" value={cPassword} onChange={e => setCPassword(e.target.value)} />
                      </div>
                      {/* поле резюме удалено — будет после регистрации */}
                    </div>
                    <div className="flex gap-2">
                      <button className="btn-primary hover-lift" onClick={registerCandidate}>Регистрация</button>
                      <button className="btn-outline hover-lift" onClick={loginCandidate}>Войти</button>
                    </div>
                    {msg && <div className="text-sm text-[#666]">{msg}</div>}
                  </section>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
