import { useEffect, useMemo, useRef, useState } from 'react'

type Props = { items: string[]; intervalMs?: number; auto?: boolean }

export default function RiskCarousel({ items, intervalMs = 3500, auto = true }: Props) {
  const slides = useMemo(() => (items || []).filter(Boolean), [items])
  const [index, setIndex] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const startX = useRef(0)
  const deltaX = useRef(0)
  const timer = useRef<number | null>(null)
  const viewportRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!auto || slides.length <= 1) return
    if (timer.current) window.clearInterval(timer.current)
    timer.current = window.setInterval(() => next(), intervalMs)
    return () => { if (timer.current) window.clearInterval(timer.current) }
  }, [slides.length, auto, intervalMs])

  const next = () => setIndex(i => (i + 1) % Math.max(slides.length, 1))
  const prev = () => setIndex(i => (i - 1 + Math.max(slides.length, 1)) % Math.max(slides.length, 1))

  const onTouchStart = (e: React.TouchEvent) => {
    if (slides.length <= 1) return
    setIsDragging(true)
    startX.current = e.touches[0].clientX
    deltaX.current = 0
    if (timer.current) window.clearInterval(timer.current)
  }
  const onTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return
    deltaX.current = e.touches[0].clientX - startX.current
    if (viewportRef.current) {
      const w = viewportRef.current.clientWidth
      viewportRef.current.style.setProperty('--drag-x', String(deltaX.current / w))
    }
  }
  const onTouchEnd = () => {
    if (!isDragging) return
    setIsDragging(false)
    const threshold = 50
    if (deltaX.current > threshold) prev()
    else if (deltaX.current < -threshold) next()
    if (viewportRef.current) viewportRef.current.style.removeProperty('--drag-x')
  }

  if (slides.length === 0) return <div className="text-[12px] text-[#666]">Зоны риска ожидают данные</div>

  return (
    <div className="relative rounded-xl border border-[#E6E8EB] bg-white select-none">
      {/* Viewport */}
      <div
        ref={viewportRef}
        className="overflow-hidden"
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <div
          className="flex transition-transform duration-300 ease-out"
          style={{ transform: `translateX(calc(${(-index) * 100}% + (var(--drag-x, 0) * 100%)))` }}
        >
          {slides.map((t, i) => (
            <div key={i} className="min-w-full p-4">
              <div className="h-24 flex items-center justify-center text-center text-[13px] leading-[18px] px-4 rounded-lg bg-[#FFF7F7] border border-[#FFE0E0] text-[#0A0A0A]">
                {t}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Arrows */}
      {slides.length > 1 && (
        <>
          <button aria-label="prev" className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-white border border-[#E6E8EB] w-7 h-7 text-[#0A0A0A]" onClick={prev}>
            ‹
          </button>
          <button aria-label="next" className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-white border border-[#E6E8EB] w-7 h-7 text-[#0A0A0A]" onClick={next}>
            ›
          </button>
          <div className="absolute -bottom-2 left-0 right-0 flex items-center justify-center gap-1 pb-1">
            {slides.map((_, i) => (
              <button key={i} aria-label={`slide ${i + 1}`} className={`w-1.5 h-1.5 rounded-full ${i === index ? 'bg-[#4F46E5]' : 'bg-[#E6E8EB]'}`} onClick={() => setIndex(i)} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}


