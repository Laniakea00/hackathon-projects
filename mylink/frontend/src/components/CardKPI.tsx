import React from 'react'

type Props = {
  icon?: React.ReactNode
  title: string
  value: string | number
  delta?: number | null
}

export function CardKPI({ icon, title, value, delta = null }: Props) {
  const deltaSign = typeof delta === 'number' ? (delta > 0 ? '+' : '') : ''
  const deltaColor = typeof delta === 'number' ? (delta >= 0 ? 'text-green-600' : 'text-red-600') : 'text-grayx-500'
  return (
    <div className="rounded-2xl border border-[#E6E8EB] bg-white shadow-sm p-4 flex items-center gap-3">
      <div aria-hidden className="w-10 h-10 rounded-xl bg-[#EEF2FF] text-[#4F46E5] flex items-center justify-center">
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-[12px] leading-[18px] text-[#666] truncate">{title}</div>
        <div className="flex items-baseline gap-2">
          <div className="text-[24px] leading-[28px] font-semibold text-[#0A0A0A]">{value}</div>
          {delta !== null && (
            <span className={`text-[12px] leading-[18px] ${deltaColor}`}>{deltaSign}{delta}%</span>
          )}
        </div>
      </div>
    </div>
  )
}

export default CardKPI


