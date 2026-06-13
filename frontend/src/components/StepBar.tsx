const STEPS = ['Search', 'Analyse', 'Choose', 'Negotiate', 'Meet up']

const STATUS_STEP: Record<string, number> = {
  searching: 0, reviewing: 1, awaiting_human: 2,
  negotiating: 3, coordinating: 4, done: 4,
}

export default function StepBar({ status }: { status?: string }) {
  const active = STATUS_STEP[status ?? 'searching'] ?? 0
  return (
    <div className="flex items-center justify-center gap-0 py-3">
      {STEPS.map((label, i) => (
        <div key={label} className="flex items-center">
          <div className="flex items-center gap-1.5">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
              ${i < active ? 'bg-indigo-500 text-white' :
                i === active ? 'bg-orange-500 text-white' :
                'bg-slate-200 text-slate-400'}`}>
              {i < active ? '✓' : i + 1}
            </div>
            <span className={`text-xs font-medium
              ${i < active ? 'text-indigo-600' :
                i === active ? 'text-orange-600 font-bold' :
                'text-slate-400'}`}>{label}</span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`w-6 h-0.5 mx-1 ${i < active ? 'bg-indigo-400' : 'bg-slate-200'}`} />
          )}
        </div>
      ))}
    </div>
  )
}
