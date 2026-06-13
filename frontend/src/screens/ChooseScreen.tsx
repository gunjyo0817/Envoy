import { useState } from 'react'
import type { SessionState } from '../api'
import StepBar from '../components/StepBar'
import ListingCard from '../components/ListingCard'
import CheckpointBanner from '../components/CheckpointBanner'

interface Props { state: SessionState; onFeedback: (choice: string) => Promise<void> }

export default function ChooseScreen({ state, onFeedback }: Props) {
  const [loading, setLoading] = useState(false)
  const candidates = state.ranked_candidates ?? []
  const decision = state.pending_decision!

  const handleChoice = async (choice: string) => {
    setLoading(true)
    await onFeedback(choice)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center p-4">
      <div className="w-full max-w-md">
        <div className="text-xl font-black text-indigo-600 py-4">buybot</div>
        <StepBar status={state.status} />

        <div className="bg-white rounded-2xl shadow-lg overflow-hidden mt-4">
          <div className="px-4 pt-4 pb-2">
            <div className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-3">
              Top results · {candidates.length} candidates
            </div>
            <div className="space-y-3">
              {candidates.slice(0, 3).map((c, i) => (
                <ListingCard key={i} candidate={c} rank={i} />
              ))}
            </div>
          </div>
          <CheckpointBanner decision={decision} onChoice={handleChoice} loading={loading} />
        </div>
      </div>
    </div>
  )
}
