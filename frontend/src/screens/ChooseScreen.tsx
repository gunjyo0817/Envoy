import { useState, useEffect } from 'react'
import type { SessionState } from '../api'
import StepBar from '../components/StepBar'
import ListingCard from '../components/ListingCard'
import CheckpointBanner from '../components/CheckpointBanner'

interface Props {
  state: SessionState
  onFeedback: (choice: string) => Promise<void>
}

export default function ChooseScreen({ state, onFeedback }: Props) {
  const [loading, setLoading] = useState(false)
  const candidates = state.ranked_candidates ?? []
  const decision = state.pending_decision!

  // Re-enable buttons when this checkpoint re-renders with new content.
  useEffect(() => {
    setLoading(false)
  }, [decision?.summary])

  const handleChoice = async (choice: string) => {
    setLoading(true)
    await onFeedback(choice)
  }

  const top = candidates[0]
  const rest = candidates.slice(1, 3)

  // Cards are directly clickable: the non-cancel checkpoint options map to the
  // ranked candidates in order (option 0 → top pick, option 1 → runner-up #2…).
  const pickOptions = (decision?.options ?? []).filter((o) => o.id !== 'cancel')
  const choiceForRank = (rank: number): string | undefined => pickOptions[rank]?.id

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

      <div className="console-rise relative mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-[34rem] flex-col lg:max-w-[56rem]">
        <StepBar status={state.status} checkpoint={decision?.checkpoint} />

        <div className="mt-9 flex flex-1 flex-col">
          <h1 className="text-balance text-2xl font-bold tracking-[-0.01em] text-[var(--color-ink)]">
            {top ? 'I found your best match' : 'No matches found'}
          </h1>
          <p className="mt-2 text-sm text-[var(--color-ink-muted)]">
            {candidates.length > 0
              ? `Ranked ${candidates.length} candidate${candidates.length === 1 ? '' : 's'} by price, condition and seller trust.`
              : 'Nothing came back within your budget and condition.'}
          </p>

          {top && (
            <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-2 lg:items-start lg:gap-6">
              <ListingCard
                candidate={top}
                rank={0}
                onClick={choiceForRank(0) ? () => handleChoice(choiceForRank(0)!) : undefined}
                disabled={loading}
              />
              {rest.length > 0 && (
                <div className="space-y-3">
                  <p className="px-1 pt-1 text-xs font-medium text-[var(--color-ink-faint)] lg:pt-0">
                    Runners-up · tap to pick
                  </p>
                  {rest.map((c, i) => (
                    <ListingCard
                      key={i}
                      candidate={c}
                      rank={i + 1}
                      onClick={choiceForRank(i + 1) ? () => handleChoice(choiceForRank(i + 1)!) : undefined}
                      disabled={loading}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex-1" />

          <div className="mt-7">
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
