import { useState, useEffect } from 'react'
import type { SessionState, MeetupProposal } from '../api'
import StepBar from '../components/StepBar'
import CheckpointBanner from '../components/CheckpointBanner'

interface Props {
  state: SessionState
  onFeedback: (choice: string) => Promise<void>
}

export default function MeetupScreen({ state, onFeedback }: Props) {
  const [loading, setLoading] = useState(false)
  const decision = state.pending_decision!
  const proposal = (decision.context?.meetup_proposal ?? state.meetup_proposal) as MeetupProposal | undefined
  const agreedPrice = proposal?.final_price ?? state.final_price

  // "Reschedule" re-renders this with a fresh proposal; re-enable on new checkpoint.
  useEffect(() => {
    setLoading(false)
  }, [decision?.summary])

  const handleChoice = async (choice: string) => {
    setLoading(true)
    await onFeedback(choice)
  }

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

      <div className="console-rise relative mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-[34rem] flex-col">
        <StepBar status={state.status} checkpoint={decision?.checkpoint} />

        <div className="mt-9 flex flex-1 flex-col">
          <h1 className="text-balance text-2xl font-bold tracking-[-0.01em] text-[var(--color-ink)]">
            Here’s where you’ll meet
          </h1>

          {/* Meeting point — the hero */}
          <div className="mt-5 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <div className="flex items-start gap-3">
              <span aria-hidden className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[var(--color-accent)] text-[var(--color-accent-text)]">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
              </span>
              <div className="min-w-0">
                <p className="text-lg font-semibold leading-snug text-[var(--color-ink)]">
                  {proposal?.location ?? 'Meeting point'}
                </p>
                {proposal?.reason && (
                  <p className="mt-1 text-pretty text-sm leading-relaxed text-[var(--color-ink-muted)]">
                    {proposal.reason}
                  </p>
                )}
              </div>
            </div>

            {/* Route schematic — You → meeting point */}
            {proposal?.buyer_route?.duration_text && (
              <div className="mt-5 flex items-center gap-2">
                <span className="flex items-center gap-1.5 text-sm font-medium text-[var(--color-ink)]">
                  <span aria-hidden className="h-2 w-2 rounded-full bg-[var(--color-primary)]" />
                  You
                </span>
                <span className="relative flex flex-1 items-center" aria-hidden>
                  <span className="h-px w-full bg-[var(--color-border)]" style={{ backgroundImage: 'repeating-linear-gradient(90deg, var(--color-border) 0 5px, transparent 5px 9px)' }} />
                  <span className="absolute left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-[var(--color-surface-raised)] px-2.5 py-0.5 text-xs font-medium text-[var(--color-ink-muted)]">
                    {proposal.buyer_route.duration_text}
                  </span>
                </span>
                <span className="flex items-center gap-1.5 text-sm font-medium text-[var(--color-ink)]">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
                    <circle cx="12" cy="10" r="3" />
                  </svg>
                  Spot
                </span>
              </div>
            )}
          </div>

          {/* Time + agreed price */}
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {proposal?.time_suggestion && (
              <div className="flex items-center gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3.5">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-[var(--color-ink-muted)]" aria-hidden>
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 7v5l3 2" />
                </svg>
                <div>
                  <p className="text-xs text-[var(--color-ink-muted)]">When</p>
                  <p className="text-sm font-semibold text-[var(--color-ink)]">{proposal.time_suggestion}</p>
                </div>
              </div>
            )}
            {agreedPrice != null && (
              <div className="flex items-center gap-3 rounded-xl border border-[var(--color-accent-dim)] bg-[oklch(0.14_0.025_60)] px-4 py-3.5">
                <span aria-hidden className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--color-accent)] text-[var(--color-accent-text)] text-sm font-bold">
                  €
                </span>
                <div>
                  <p className="text-xs text-[var(--color-accent)]">Deal agreed</p>
                  <p className="text-lg font-bold tabular-nums text-[var(--color-ink)]">€{agreedPrice}</p>
                </div>
              </div>
            )}
          </div>

          <div className="flex-1" />

          <div className="mt-7">
            <CheckpointBanner
              decision={decision}
              onChoice={handleChoice}
              loading={loading}
              eyebrow="Final step"
            />
          </div>
        </div>
      </div>
    </main>
  )
}
