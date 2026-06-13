import { useState, useEffect } from 'react'
import type { SessionState } from '../api'
import StepBar from '../components/StepBar'
import NegotiationThread from '../components/NegotiationThread'
import CheckpointBanner from '../components/CheckpointBanner'

interface Props {
  state: SessionState
  onFeedback: (choice: string) => Promise<void>
}

export default function NegotiateScreen({ state, onFeedback }: Props) {
  const [loading, setLoading] = useState(false)
  const thread = state.negotiation_thread ?? []
  const decision = state.pending_decision!
  const listing = state.ranked_candidates?.[state.current_candidate_index ?? 0]

  // Both negotiation rounds render here (both confirm_offer); re-enable the
  // buttons whenever a fresh checkpoint arrives.
  useEffect(() => {
    setLoading(false)
  }, [decision?.summary])

  const handleChoice = async (choice: string) => {
    setLoading(true)
    await onFeedback(choice)
  }

  // Latest price on the table, for the price rail.
  const latestPriced = [...thread].reverse().find((m) => m.price != null)
  const onTable = latestPriced?.price ?? listing?.price_eur

  return (
    <main className="relative min-h-dvh overflow-hidden bg-[var(--color-bg)] px-5 py-10 sm:px-6">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 opacity-70"
        style={{
          background:
            'radial-gradient(60% 120% at 50% 0%, oklch(0.75 0.16 60 / 0.12), transparent 70%)',
        }}
      />

      <div className="console-rise relative mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-[34rem] flex-col lg:max-w-[48rem]">
        <StepBar status={state.status} checkpoint={decision?.checkpoint} />

        <div className="mt-9 flex flex-1 flex-col">
          {/* What we're negotiating */}
          {listing && (
            <header className="w-full lg:mx-auto lg:max-w-[42rem]">
              <h1 className="text-balance text-xl font-bold leading-snug tracking-[-0.01em] text-[var(--color-ink)]">
                {listing.title}
              </h1>
              <div className="mt-3 flex items-center gap-3 text-sm">
                <span className="text-[var(--color-ink-muted)]">
                  Listed <span className="font-semibold tabular-nums text-[var(--color-ink)]">€{listing.price_eur}</span>
                </span>
                {onTable != null && onTable !== listing.price_eur && (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--color-ink-faint)]" aria-hidden>
                      <path d="M5 12h14M13 6l6 6-6 6" />
                    </svg>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--color-accent)] px-2.5 py-1 text-xs font-semibold text-[var(--color-accent-text)]">
                      On the table €{onTable}
                    </span>
                  </>
                )}
              </div>
            </header>
          )}

          {/* The conversation */}
          <div className="mt-6 w-full lg:mx-auto lg:max-w-[42rem]">
            {thread.length > 0 ? (
              <NegotiationThread thread={thread} />
            ) : (
              <p className="text-sm text-[var(--color-ink-muted)]">Opening the conversation…</p>
            )}
          </div>

          <div className="flex-1" />

          <div className="mt-7 w-full lg:mx-auto lg:max-w-[42rem]">
            <CheckpointBanner
              decision={decision}
              onChoice={handleChoice}
              loading={loading}
              eyebrow="Your call"
            />
          </div>
        </div>
      </div>
    </main>
  )
}
