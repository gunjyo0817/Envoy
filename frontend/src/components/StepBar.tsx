const STEPS = ['Search', 'Analyse', 'Choose', 'Negotiate', 'Meet up']

const STATUS_STEP: Record<string, number> = {
  searching: 0,
  reviewing: 1,
  awaiting_human: 2,
  negotiating: 3,
  awaiting_seller: 3,
  coordinating: 4,
  done: 5,
}

// When paused at a human checkpoint, the checkpoint pins the exact step.
const CHECKPOINT_STEP: Record<string, number> = {
  confirm_candidate: 2,
  confirm_offer: 3,
  confirm_meetup: 4,
}

interface Props {
  status?: string
  checkpoint?: string
}

export default function StepBar({ status, checkpoint }: Props) {
  let active = STATUS_STEP[status ?? 'searching'] ?? 0
  if (status === 'awaiting_human' && checkpoint && CHECKPOINT_STEP[checkpoint] != null) {
    active = CHECKPOINT_STEP[checkpoint]
  }
  const currentIndex = Math.min(active, STEPS.length - 1)
  const done = status === 'done'

  return (
    <nav aria-label="Progress" className="w-full">
      <ol className="flex items-center">
        {STEPS.map((label, i) => {
          const isDone = i < active
          const isCurrent = i === currentIndex && !done
          return (
            <li
              key={label}
              className="flex items-center"
              style={{ flex: i < STEPS.length - 1 ? '1 1 0%' : '0 0 auto' }}
              aria-current={isCurrent ? 'step' : undefined}
            >
              <span className="relative flex h-3 w-3 shrink-0 items-center justify-center">
                {isCurrent && (
                  <span
                    aria-hidden
                    className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--color-primary)] opacity-60"
                  />
                )}
                <span
                  className={`relative h-3 w-3 rounded-full transition-colors ${
                    isDone || isCurrent
                      ? 'bg-[var(--color-primary)]'
                      : 'bg-[var(--color-surface-raised)] ring-1 ring-[var(--color-border)]'
                  }`}
                >
                  {isDone && (
                    <svg
                      viewBox="0 0 24 24"
                      className="absolute inset-0 h-3 w-3 text-[var(--color-primary-text)]"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="4"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden
                    >
                      <path d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </span>
              </span>
              {i < STEPS.length - 1 && (
                <span className="mx-1.5 h-px flex-1 overflow-hidden rounded-full bg-[var(--color-border)]">
                  <span
                    className="block h-full bg-[var(--color-primary)] transition-[width] duration-500"
                    style={{ width: i < active ? '100%' : '0%' }}
                  />
                </span>
              )}
            </li>
          )
        })}
      </ol>
      <p className="mt-2.5 text-xs font-medium text-[var(--color-ink-muted)]">
        {done ? (
          <span className="text-[var(--color-primary)]">Complete</span>
        ) : (
          <>
            <span className="text-[var(--color-ink)]">{STEPS[currentIndex]}</span>
            <span className="text-[var(--color-ink-faint)]"> · step {currentIndex + 1} of {STEPS.length}</span>
          </>
        )}
      </p>
    </nav>
  )
}
