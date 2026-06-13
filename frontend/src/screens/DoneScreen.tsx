import type { SessionState } from '../api'

export default function DoneScreen({ state }: { state: SessionState }) {
  const p = state.meetup_proposal

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md text-center">
        <div className="text-5xl mb-4">🎉</div>
        <div className="text-xl font-black text-slate-800 mb-1">You're all set!</div>
        <div className="text-slate-500 text-sm mb-6">
          buybot handled the search, negotiation, and scheduling — you just showed up.
        </div>
        <div className="bg-slate-50 rounded-xl p-4 text-left space-y-2 mb-6">
          <div className="flex items-center gap-2 text-sm">
            <span>📍</span>
            <span className="font-semibold text-slate-700">{p?.location}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span>🕐</span>
            <span className="text-slate-600">{p?.time_suggestion}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span>💰</span>
            <span className="font-bold text-emerald-600">€{p?.final_price} agreed</span>
          </div>
        </div>
        <button onClick={() => window.location.href = '/'}
          className="w-full bg-indigo-600 text-white font-bold py-3 rounded-xl text-sm">
          Start a new search
        </button>
      </div>
    </div>
  )
}
