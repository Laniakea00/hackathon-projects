import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

type Message = { role: 'user' | 'assistant'; text: string }

export default function EmployerAssistant({ vacancyId, onClose }: { vacancyId: string; onClose: () => void }) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', text: 'Здравствуйте! Я помогу сравнить кандидатов и выбрать лучшего. Спросите: "топ кандидат", "сравни Иван и Мария", "пересчитай всех".' },
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const boxRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => { boxRef.current?.scrollTo({ top: boxRef.current.scrollHeight }) }, [messages])

  const send = async () => { if (input.trim()) { await processInput(input.trim()); setInput('') } }

  const processInput = async (text: string) => {
    setMessages(m => [...m, { role: 'user', text }])
    setBusy(true)
    try {
      // Try LLM-backed assistant endpoint first for arbitrary questions
      if (!['топ','сравни','пересчитай'].some(k => text.toLowerCase().includes(k))) {
        try {
          const r = await api.post('/ai/employer/assistant', { vacancy_id: vacancyId, question: text })
          await typeAssistant(r.data.answer || 'Нет ответа')
          return
        } catch {}
      }
      const lower = text.toLowerCase()
      if (lower.includes('пересчитай') || lower.includes('пересчитать') || lower.includes('rescore')) {
        await rescoreAll(); return
      }
      if (lower.startsWith('топ') || lower.includes('top')) { await showTop(); return }
      if (lower.includes('сравни') || lower.includes('compare')) { await comparePair(lower); return }
      await bestCandidateExplanation()
    } catch {
      await typeAssistant('Произошла ошибка. Попробуйте ещё раз.')
    } finally { setBusy(false) }
  }

  const rescoreAll = async () => {
    await typeAssistant('Пересчитываю всех кандидатов…')
    // Получаем отклики по вакансии и прогоняем пайплайн для тех, у кого нет relevance_score
    const r = await api.get(`/responses?vacancy_id=${vacancyId}`)
    const list = r.data as any[]
    for (const it of list) {
      try {
        await api.post('/ai/pipeline/screen_by_ids', { vacancy_id: vacancyId, candidate_id: it.candidate_id, response_id: it.id, limits: { max_questions: 0 } })
      } catch {}
    }
    await typeAssistant('Готово. Обновите список — метрики пересчитаны.')
  }

  const showTop = async () => {
    const r = await api.get(`/responses?vacancy_id=${vacancyId}`)
    const list = (r.data as any[]).slice().sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0))
    const top = list.slice(0, 3).map((x, i) => `${i + 1}) ${x.candidate_name} — ${Math.round((x.relevance_score || 0) * 100)}%`).join('\n') || 'Данных пока нет'
    await typeAssistant(`Топ кандидатов:\n${top}`)
  }

  const comparePair = async (_: string) => {
    const r = await api.get(`/responses?vacancy_id=${vacancyId}`)
    const list = r.data as any[]
    // простая эвристика: возьмём первых двух по score
    const sorted = list.slice().sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0))
    if (sorted.length < 2) {
      setMessages(m => [...m, { role: 'assistant', text: 'Недостаточно кандидатов для сравнения.' }])
      return
    }
    const [a, b] = sorted
    const ans =
      `Сравнение:\n` +
      `${a.candidate_name} vs ${b.candidate_name}\n` +
      `Overall: ${pct(a.relevance_score)}% vs ${pct(b.relevance_score)}%\n` +
      `Skills: ${s(a,'skills')} vs ${s(b,'skills')} | Exp: ${s(a,'experience')} vs ${s(b,'experience')}\n` +
      `Langs: ${s(a,'langs')} | Loc: ${s(a,'location')} | Domain: ${s(a,'domain')} | Comp: ${s(a,'comp')}`
    await typeAssistant(ans)
  }

  function s(x: any, k: string) { return Math.round(((x.rejection_reasons?.scores_pct?.[k] ?? 0) as number)) + '%' }
  function pct(v?: number) { return Math.round(((v || 0) * 100)) }

  const bestCandidateExplanation = async () => {
    const r = await api.get(`/responses?vacancy_id=${vacancyId}`)
    const list = (r.data as any[]).slice().sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0))
    if (!list.length) { await typeAssistant('Пока нет откликов для анализа.'); return }
    const top = list[0]
    if (!top.rejection_reasons) {
      try { await api.post('/ai/pipeline/screen_by_ids', { vacancy_id: vacancyId, candidate_id: top.candidate_id, response_id: top.id, limits: { max_questions: 0 } }) } catch {}
    }
    const refreshed = (await api.get(`/responses?vacancy_id=${vacancyId}`)).data as any[]
    const best = refreshed.find(x => x.id === top.id) || top
    const pos = (best.rejection_reasons?.summary?.positives || []).slice(0, 3).join('; ') || '—'
    const risks = (best.rejection_reasons?.summary?.risks || []).slice(0, 3).join('; ') || '—'
    const ans = `Лучший кандидат: ${best.candidate_name} (${pct(best.relevance_score)}%).\nСильные стороны: ${pos}.\nРиски: ${risks}.`
    await typeAssistant(ans)
  }

  // Typewriter effect for assistant messages
  const typeAssistant = async (text: string) => {
    let insertIndex = -1
    setMessages(m => { insertIndex = m.length; return [...m, { role: 'assistant', text: '' }] })
    const speed = 15
    for (let i = 1; i <= text.length; i++) {
      await new Promise(res => setTimeout(res, speed))
      const slice = text.slice(0, i)
      setMessages(m => {
        const arr = m.slice()
        if (arr[insertIndex]) arr[insertIndex] = { role: 'assistant', text: slice }
        return arr
      })
    }
  }

  return (
    <div className="fixed inset-0 z-[70]">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full max-w-[520px] bg-white border-l border-[#E6E8EB] shadow-lg flex flex-col">
        <header className="px-4 py-3 border-b border-[#E6E8EB]">
          <div className="flex items-center justify-between"><div className="font-semibold">Assistant</div><button className="btn-outline" onClick={onClose}>Закрыть</button></div>
          <div className="mt-2 flex flex-wrap gap-2 text-[12px]">
            <button className="tab" onClick={() => { void processInput('топ') }}>топ</button>
            <button className="tab" onClick={() => { void processInput('сравни') }}>сравни</button>
            <button className="tab" onClick={() => { void processInput('пересчитай') }}>пересчитай</button>
            <button className="tab" onClick={() => { void processInput('лучший кандидат и почему') }}>лучший и почему</button>
          </div>
        </header>
        <div ref={boxRef} className="flex-1 overflow-auto p-4 space-y-2">
          {messages.map((m, i) => (
            <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
              <span className={m.role === 'user' ? 'inline-block bg-[#2E6BFF] text-white px-3 py-2 rounded-xl' : 'inline-block bg-[#F7F8FA] px-3 py-2 rounded-xl border border-[#E6E8EB]'}>{m.text}</span>
            </div>
          ))}
          {busy && <div className="text-[12px] text-[#666]">Печатаю…</div>}
        </div>
        <footer className="p-3 border-t border-[#E6E8EB] flex items-center gap-2">
          <input className="flex-1 border border-[#E6E8EB] rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-[#2E6BFF]" placeholder="Спросите: топ, сравни, пересчитай…" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' ? send() : undefined} />
          <button className="btn-primary" onClick={send} disabled={busy}>Отправить</button>
        </footer>
      </div>
    </div>
  )
}


