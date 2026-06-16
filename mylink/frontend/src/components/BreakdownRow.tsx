export function BreakdownRow({ label, pct }: { label: string; pct: number | null | undefined }) {
  if (pct === null || pct === undefined) return null
  const value = Math.max(0, Math.min(100, Math.round(pct)))
  const bar = value >= 75 ? '#16A34A' : value >= 60 ? '#F59E0B' : '#DC2626'
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[12px] leading-[18px] text-[#0A0A0A]">
        <span className="text-[#666]">{label}</span>
        <span>{value}%</span>
      </div>
      <div className="h-2 rounded-full bg-[#F1F3F5] overflow-hidden">
        <div className="h-full" style={{ width: `${value}%`, background: bar }} />
      </div>
    </div>
  )
}

export default BreakdownRow


