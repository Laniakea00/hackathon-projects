import { useMemo } from 'react'

type Props = {
  value: string
  onChange: (next: string) => void
  delimiter?: string
  placeholder?: string
}

export function TokenInput({ value, onChange, delimiter = ',', placeholder }: Props) {
  const tokens = useMemo(() => value.split(delimiter).map(s => s.trim()).filter(Boolean), [value, delimiter])
  return (
    <div>
      <input
        className="border border-[#E6E8EB] rounded-xl px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-[#4F46E5]"
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
      />
      {tokens.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {tokens.map((t, i) => (
            <span key={i} className="text-[12px] px-2 py-1 rounded-full bg-[#F7F8FA] border border-[#E6E8EB] text-[#0A0A0A]">{t}</span>
          ))}
        </div>
      )}
      <div className="text-[12px] leading-[18px] text-[#666] mt-1">Введите через «{delimiter}»</div>
    </div>
  )
}

export default TokenInput


