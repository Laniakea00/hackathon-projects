import { useEffect, useState } from 'react'
import { api } from '../lib/api'

export default function ResumeEditor() {
  const [candidateId, setCandidateId] = useState<string | null>(() => {
    try { return localStorage.getItem('candidate_id') } catch { return null }
  })
  const [profile, setProfile] = useState<any>({
    basics: { full_name: '', email: '', city: '' },
    summary: '',
    skills: [''],
    experience: [{ company: '', title: '', start: '', end: '', description: '' }],
    education: [{ place: '', degree: '', start: '', end: '' }],
    certificates: [{ name: '', issuer: '', year: '' }],
  })
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const load = async () => {
      if (!candidateId) return
      try {
        const r = await api.get(`/candidates/${candidateId}/profile`)
        setProfile({ ...profile, ...r.data })
      } catch {}
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId])

  const save = async () => {
    if (!candidateId) { setErr('Сначала загрузите резюме PDF или откликнитесь в каталоге'); return }
    setBusy(true); setMsg(''); setErr('')
    try {
      await api.put(`/candidates/${candidateId}/profile`, profile)
      setMsg('Профиль сохранён')
    } catch { setErr('Не удалось сохранить профиль') } finally { setBusy(false) }
  }

  const uploadPdf = async () => {
    if (!pdfFile) { setErr('Выберите PDF'); return }
    if (!profile.basics.full_name || !profile.basics.email) { setErr('Заполните ФИО и Email'); return }
    setBusy(true); setMsg(''); setErr('')
    try {
      const form = new FormData()
      form.append('file', pdfFile)
      form.append('full_name', profile.basics.full_name)
      form.append('email', profile.basics.email)
      form.append('city', profile.basics.city || '')
      const r = await api.post('/candidates/upload_pdf', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      const id = r.data.id as string
      setCandidateId(id)
      try { localStorage.setItem('candidate_id', id) } catch {}
      setMsg('PDF загружен, черновик профиля создан')
    } catch { setErr('Загрузка не удалась') } finally { setBusy(false) }
  }

  return (
    <div className="container py-6 space-y-4">
      <h1 className="text-[28px] leading-[36px] font-semibold">Страница резюме</h1>

      {/* Basics */}
      <section className="card p-4 space-y-2">
        <h2 className="text-lg font-semibold">Основное</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input className="border rounded px-3 py-2" placeholder="ФИО" value={profile.basics.full_name} onChange={e => setProfile({ ...profile, basics: { ...profile.basics, full_name: e.target.value } })} />
          <input className="border rounded px-3 py-2" placeholder="Email" value={profile.basics.email} onChange={e => setProfile({ ...profile, basics: { ...profile.basics, email: e.target.value } })} />
          <input className="border rounded px-3 py-2" placeholder="Город" value={profile.basics.city} onChange={e => setProfile({ ...profile, basics: { ...profile.basics, city: e.target.value } })} />
        </div>
        <textarea className="border rounded px-3 py-2" placeholder="Кратко о себе" value={profile.summary} onChange={e => setProfile({ ...profile, summary: e.target.value })} />
        <div className="flex items-center gap-2">
          <input type="file" accept="application/pdf" onChange={e => setPdfFile(e.target.files?.[0] || null)} />
          <button className="btn-outline" onClick={uploadPdf} disabled={busy}>Загрузить PDF</button>
        </div>
      </section>

      {/* Skills */}
      <section className="card p-4 space-y-2">
        <h2 className="text-lg font-semibold">Навыки</h2>
        <div className="flex flex-wrap gap-2">
          {profile.skills.map((s: string, i: number) => (
            <input key={i} className="border rounded px-3 py-2" value={s} onChange={e => {
              const next = [...profile.skills]; next[i] = e.target.value; setProfile({ ...profile, skills: next })
            }} />
          ))}
          <button className="btn-outline" onClick={() => setProfile({ ...profile, skills: [...profile.skills, ''] })}>Добавить</button>
        </div>
      </section>

      {/* Experience */}
      <section className="card p-4 space-y-2">
        <h2 className="text-lg font-semibold">Опыт работы</h2>
        {profile.experience.map((e: any, i: number) => (
          <div key={i} className="grid grid-cols-1 md:grid-cols-4 gap-2">
            <input className="border rounded px-3 py-2" placeholder="Компания" value={e.company} onChange={ev => { const next = [...profile.experience]; next[i].company = ev.target.value; setProfile({ ...profile, experience: next }) }} />
            <input className="border rounded px-3 py-2" placeholder="Должность" value={e.title} onChange={ev => { const next = [...profile.experience]; next[i].title = ev.target.value; setProfile({ ...profile, experience: next }) }} />
            <input className="border rounded px-3 py-2" placeholder="Начало YYYY-MM" value={e.start} onChange={ev => { const next = [...profile.experience]; next[i].start = ev.target.value; setProfile({ ...profile, experience: next }) }} />
            <input className="border rounded px-3 py-2" placeholder="Конец YYYY-MM / по наст." value={e.end} onChange={ev => { const next = [...profile.experience]; next[i].end = ev.target.value; setProfile({ ...profile, experience: next }) }} />
            <textarea className="border rounded px-3 py-2 md:col-span-4" placeholder="Описание" value={e.description} onChange={ev => { const next = [...profile.experience]; next[i].description = ev.target.value; setProfile({ ...profile, experience: next }) }} />
          </div>
        ))}
        <button className="btn-outline" onClick={() => setProfile({ ...profile, experience: [...profile.experience, { company: '', title: '', start: '', end: '', description: '' }] })}>Добавить опыт</button>
      </section>

      {/* Education */}
      <section className="card p-4 space-y-2">
        <h2 className="text-lg font-semibold">Образование</h2>
        {profile.education.map((e: any, i: number) => (
          <div key={i} className="grid grid-cols-1 md:grid-cols-4 gap-2">
            <input className="border rounded px-3 py-2" placeholder="Учебное заведение" value={e.place} onChange={ev => { const next = [...profile.education]; next[i].place = ev.target.value; setProfile({ ...profile, education: next }) }} />
            <input className="border rounded px-3 py-2" placeholder="Степень/направление" value={e.degree} onChange={ev => { const next = [...profile.education]; next[i].degree = ev.target.value; setProfile({ ...profile, education: next }) }} />
            <input className="border rounded px-3 py-2" placeholder="Начало YYYY-MM" value={e.start} onChange={ev => { const next = [...profile.education]; next[i].start = ev.target.value; setProfile({ ...profile, education: next }) }} />
            <input className="border rounded px-3 py-2" placeholder="Конец YYYY-MM/ожидается" value={e.end} onChange={ev => { const next = [...profile.education]; next[i].end = ev.target.value; setProfile({ ...profile, education: next }) }} />
          </div>
        ))}
        <button className="btn-outline" onClick={() => setProfile({ ...profile, education: [...profile.education, { place: '', degree: '', start: '', end: '' }] })}>Добавить образование</button>
      </section>

      {/* Certificates */}
      <section className="card p-4 space-y-2">
        <h2 className="text-lg font-semibold">Сертификаты</h2>
        {profile.certificates.map((c: any, i: number) => (
          <div key={i} className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <input className="border rounded px-3 py-2" placeholder="Название" value={c.name} onChange={ev => { const next = [...profile.certificates]; next[i].name = ev.target.value; setProfile({ ...profile, certificates: next }) }} />
            <input className="border rounded px-3 py-2" placeholder="Выдавшая организация" value={c.issuer} onChange={ev => { const next = [...profile.certificates]; next[i].issuer = ev.target.value; setProfile({ ...profile, certificates: next }) }} />
            <input className="border rounded px-3 py-2" placeholder="Год" value={c.year} onChange={ev => { const next = [...profile.certificates]; next[i].year = ev.target.value; setProfile({ ...profile, certificates: next }) }} />
          </div>
        ))}
        <button className="btn-outline" onClick={() => setProfile({ ...profile, certificates: [...profile.certificates, { name: '', issuer: '', year: '' }] })}>Добавить сертификат</button>
      </section>

      <div className="flex gap-2">
        <button className="btn-primary" onClick={save} disabled={busy}>Сохранить</button>
      </div>
      {msg && <div className="text-sm text-success-600">{msg}</div>}
      {err && <div className="text-sm text-danger-600">{err}</div>}
    </div>
  )
}
