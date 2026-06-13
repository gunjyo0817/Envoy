import type { PendingDecision } from '../api'

interface Props {
  decision: PendingDecision
  onChoice: (id: string) => void
  loading?: boolean
}

export default function CheckpointBanner({ decision, onChoice, loading }: Props) {
  return (
    <div className="bg-amber-50 border-t-2 border-amber-400 px-4 py-4">
      <div className="flex items-start gap-3 mb-3">
        <span className="text-2xl">🎯</span>
        <div>
          <div className="font-bold text-amber-900 text-sm">{decision.summary}</div>
        </div>
      </div>
      <div className="flex gap-2 flex-wrap">
        {decision.options.map(opt => (
          <button key={opt.id}
            disabled={loading}
            onClick={() => onChoice(opt.id)}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-colors
              ${opt.id === decision.options[0].id
                ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  )
}
