import { useState } from 'react'
import { api } from '../lib/api'
import TokenInput from './TokenInput'

type Props = {
  open: boolean
  onClose: () => void
  onCreated?: () => Promise<void> | void
}

export default function SheetCreateJob({ open, onClose, onCreated }: Props) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Form
  const [title, setTitle] = useState('')
  const [location, setLocation] = useState('')
  const [description, setDescription] = useState('')
  const [mustHave, setMustHave] = useState('')
  const [niceToHave, setNiceToHave] = useState('')
  const [minExp, setMinExp] = useState<number | ''>('')
  const [salaryMin, setSalaryMin] = useState<number | ''>('')
  const [salaryMax, setSalaryMax] = useState<number | ''>('')
  const [langs, setLangs] = useState('')

  const reset = () => {
    setStep(1); setError('')
    setTitle(''); setLocation(''); setDescription('')
    setMustHave(''); setNiceToHave(''); setMinExp('')
    setSalaryMin(''); setSalaryMax(''); setLangs('')
  }

  const close = () => { if (!loading) { reset(); onClose() } }

  const submit = async (_publish: boolean) => {
    setError('')
    if (!title.trim() || !location.trim()) {
      setError('Заполните обязательные поля: название, город/формат')
      setStep(1)
      return
    }
    setLoading(true)
    try {
      const req: any = {
        title: title.trim(),
        description: description.trim() || '-',
        location: location.trim(),
        salary_min: salaryMin === '' ? null : Number(salaryMin),
        salary_max: salaryMax === '' ? null : Number(salaryMax),
        requirements: {
          stack: mustHave.split(',').map(s => s.trim().toLowerCase()).filter(Boolean),
          nice: niceToHave.split(',').map(s => s.trim().toLowerCase()).filter(Boolean),
          min_experience_years: minExp === '' ? null : Number(minExp),
          langs: langs.split(',').map(s => s.trim()).filter(Boolean),
        }
      }
      await api.post('/vacancies', req)
      if (onCreated) await onCreated()
      close()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка создания вакансии')
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div role="dialog" aria-modal className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/20" onClick={close} />
      <div className="absolute right-0 top-0 h-full w-full max-w-[520px] bg-white shadow-xl border-l border-[#E6E8EB] flex flex-col">
        <header className="px-5 py-4 border-b border-[#E6E8EB] flex items-center justify-between">
          <div className="text-[18px] font-semibold">Новая вакансия</div>
          <button className="btn-outline" onClick={close}>Закрыть</button>
        </header>
        <div className="px-5 py-4 overflow-auto flex-1 space-y-4">
          <Steps step={step} />
          {step === 1 && (
            <section className="space-y-3">
              <Field label="Название*">
                <input className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#4F46E5] outline-none" value={title} onChange={e => setTitle(e.target.value)} placeholder="Напр. Python Developer" />
              </Field>
              <Field label="Город / формат*">
                <input className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#4F46E5] outline-none" value={location} onChange={e => setLocation(e.target.value)} placeholder="Алматы / офис" />
              </Field>
              <Field label="Описание">
                <textarea className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full min-h-28 focus:ring-2 focus:ring-[#4F46E5] outline-none" value={description} onChange={e => setDescription(e.target.value)} placeholder="Краткое описание обязанностей и стека" />
              </Field>
            </section>
          )}
          {step === 2 && (
            <section className="space-y-3">
              <Field label="Must‑have стек">
                <TokenInput value={mustHave} onChange={setMustHave} placeholder="python, fastapi, postgresql" />
                <div className="text-[12px] leading-[18px] text-[#666]">Этот список используется ИИ для приоритизации</div>
              </Field>
              <Field label="Nice‑to‑have">
                <TokenInput value={niceToHave} onChange={setNiceToHave} placeholder="docker, kubernetes" />
              </Field>
              <Field label="Мин. опыт (лет)">
                <input type="number" className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#4F46E5] outline-none" value={minExp} onChange={e => setMinExp(e.target.value === '' ? '' : Number(e.target.value))} />
              </Field>
            </section>
          )}
          {step === 3 && (
            <section className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Зарплата мин (KZT)"><input type="number" className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#4F46E5] outline-none" value={salaryMin} onChange={e => setSalaryMin(e.target.value === '' ? '' : Number(e.target.value))} /></Field>
                <Field label="Зарплата макс (KZT)"><input type="number" className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:ring-2 focus:ring-[#4F46E5] outline-none" value={salaryMax} onChange={e => setSalaryMax(e.target.value === '' ? '' : Number(e.target.value))} /></Field>
              </div>
              <Field label="Языки (CEFR)"><TokenInput value={langs} onChange={setLangs} placeholder="EN B2, RU C2" /></Field>
            </section>
          )}
          {error && <div className="text-[12px] text-[#DC2626]" role="alert" aria-live="polite">{error}</div>}
        </div>
        <footer className="px-5 py-4 border-t border-[#E6E8EB] flex items-center justify-between">
          <div className="text-[12px] text-[#666]">Шаг {step} из 3</div>
          <div className="flex gap-2">
            {step > 1 && <button className="btn-outline" onClick={() => setStep((step - 1) as any)} disabled={loading}>Назад</button>}
            {step < 3 && <button className="btn-primary" onClick={() => setStep((step + 1) as any)} disabled={loading}>Далее</button>}
            {step === 3 && (
              <>
                <button className="btn-outline" onClick={() => submit(false)} disabled={loading}>Сохранить как черновик</button>
                <button className="btn-primary" onClick={() => submit(true)} disabled={loading}>Опубликовать</button>
              </>
            )}
          </div>
        </footer>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-[12px] leading-[18px] text-[#666] mb-1">{label}</div>
      {children}
    </label>
  )
}

function Steps({ step }: { step: number }) {
  return (
    <div className="flex items-center gap-2 text-[12px] text-[#666]">
      <Dot active={step >= 1}>Основное</Dot>
      <span className="opacity-60">—</span>
      <Dot active={step >= 2}>Требования</Dot>
      <span className="opacity-60">—</span>
      <Dot active={step >= 3}>Оффер</Dot>
    </div>
  )
}

function Dot({ active, children }: { active: boolean; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 ${active ? 'text-[#0A0A0A]' : ''}`}>
      <span className={`w-2 h-2 rounded-full ${active ? 'bg-[#4F46E5]' : 'bg-[#E6E8EB]'}`} />
      {children}
    </span>
  )
}


