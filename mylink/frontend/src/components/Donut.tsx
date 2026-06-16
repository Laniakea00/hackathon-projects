// no explicit React import needed with automatic runtime

type Threshold = { min?: number; max?: number; color: string }

export function Donut({ value, size = 140, colorByThresholds = [] as Threshold[] }: { value: number; size?: number; colorByThresholds?: Threshold[] }) {
  const radius = size / 2
  const stroke = 10
  const c = 2 * Math.PI * (radius - stroke)
  const pct = Math.max(0, Math.min(100, value))
  const dash = (pct / 100) * c
  const color = pickColor(pct, colorByThresholds) || '#16A34A'
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="rotate-[-90deg]">
        <circle cx={radius} cy={radius} r={radius - stroke} stroke="#E6E8EB" strokeWidth={stroke} fill="none" />
        <circle cx={radius} cy={radius} r={radius - stroke} stroke={color} strokeWidth={stroke} fill="none" strokeDasharray={`${dash} ${c - dash}`} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-[22px] font-semibold text-[#0A0A0A]">{pct}%</div>
        </div>
      </div>
    </div>
  )
}

function pickColor(v: number, thresholds: Threshold[]): string | null {
  for (const t of thresholds) {
    const min = typeof t.min === 'number' ? t.min : -Infinity
    const max = typeof t.max === 'number' ? t.max : Infinity
    if (v > min && v <= max) return t.color
  }
  return null
}

export default Donut


