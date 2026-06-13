import { useState, useEffect } from 'react'
import type { SessionState } from '../api'
import StepBar from '../components/StepBar'
import CheckpointBanner from '../components/CheckpointBanner'

interface Props { state: SessionState; onFeedback: (choice: string) => Promise<void> }

export default function MeetupScreen({ state, onFeedback }: Props) {
  const [loading, setLoading] = useState(false)
  const decision = state.pending_decision!
  const proposal = decision.context.meetup_proposal as any

  // "Reschedule" re-renders this same component with a fresh proposal;
  // re-enable the buttons when a new checkpoint arrives.
  useEffect(() => { setLoading(false) }, [decision?.summary])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center p-4">
      <div className="w-full max-w-md">
        <div className="text-xl font-black text-indigo-600 py-4">buybot</div>
        <StepBar status="coordinating" />

        <div className="bg-white rounded-2xl shadow-lg overflow-hidden mt-4">
          <div className="px-4 pt-4 pb-3">
            <div className="text-xs text-slate-400 uppercase tracking-wide font-semibold mb-3">Meetup plan</div>

            <div className="bg-slate-50 rounded-xl p-4 space-y-3">
              <div className="flex items-start gap-3">
                <span className="text-xl">📍</span>
                <div>
                  <div className="font-bold text-slate-800">{proposal?.location}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{proposal?.reason}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xl">🕐</span>
                <div className="font-semibold text-slate-700">{proposal?.time_suggestion}</div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xl">🚇</span>
                <div className="text-slate-600 text-sm">
                  {proposal?.buyer_route?.duration_text} from you
                </div>
              </div>
              {state.final_price && (
                <div className="flex items-center gap-3">
                  <span className="text-xl">💰</span>
                  <div className="font-bold text-emerald-600 text-lg">
                    Agreed: €{state.final_price}
                  </div>
                </div>
              )}
            </div>
          </div>
          <CheckpointBanner
            decision={decision}
            onChoice={async (c) => { setLoading(true); await onFeedback(c) }}
            loading={loading}
          />
        </div>
      </div>
    </div>
  )
}
