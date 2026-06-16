export function EmptyState({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="text-center p-8 border border-dashed border-[#E6E8EB] rounded-2xl bg-white">
      <div className="text-[18px] leading-[24px] font-medium text-[#0A0A0A]">{title}</div>
      {description && <div className="text-[14px] text-[#666] mt-1">{description}</div>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}

export default EmptyState


