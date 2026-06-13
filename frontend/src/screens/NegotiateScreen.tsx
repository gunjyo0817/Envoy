import { useState, useEffect } from 'react'
import type { SessionState } from '../api'
import StepBar from '../components/StepBar'
import NegotiationThread from '../components/NegotiationThread'
import CheckpointBanner from '../components/CheckpointBanner'

interface Props { state: SessionState; onFeedback: (choice: string) => Promise<void> }

export default function NegotiateScreen({ state, onFeedback }: Props) {
  const [loading, setLoading] = useState(false)
  const thread = state.negotiation_thread ?? []
  const decision = state.pending_decision!
  const listing = state.ranked_candidates?.[0]

  // Round 1 and round 2 both render this same component (both confirm_offer),
  // so re-enable the buttons whenever a new checkpoint arrives.
  useEffect(() => { setLoading(false) }, [decision?.summary])

  const handleChoice = async (choice: string) => {
    setLoading(true)
    await onFeedback(choice)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center p-4">
      <div className="w-full max-w-md">
        <div className="text-xl font-black text-indigo-600 py-4">buybot</div>
        <StepBar status="negotiating" />

        <div className="bg-white rounded-2xl shadow-lg overflow-hidden mt-4">
          {listing && (
            <div className="px-4 pt-4 pb-2 border-b border-slate-100">
              <div className="text-xs text-slate-400 uppercase tracking-wide font-semibold">Negotiating</div>
              <div className="font-semibold text-slate-800 text-sm mt-0.5 truncate">{listing.title}</div>
              <div className="text-slate-500 text-xs">Listed at €{listing.price_eur}</div>
            </div>
          )}
          <NegotiationThread thread={thread} />
          <CheckpointBanner decision={decision} onChoice={handleChoice} loading={loading} />
        </div>
      </div>
    </div>
  )
}
