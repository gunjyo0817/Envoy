import { useEffect, useState, type ReactNode } from 'react'
import StepBar from '../components/StepBar'

interface Phase {
  title: string
  sub: string
  steps: string[]
  icon: ReactNode
}

const ICON_PROPS = {
  width: 26,
  height: 26,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

const PHASES: Record<string, Phase> = {
  searching: {
    title: 'Scanning the market',
    sub: 'Looking across every marketplace for items that match.',
    steps: ['Querying Kleinanzeigen', 'Checking Vinted', 'Scanning Facebook Marketplace'],
    icon: (
      <svg {...ICON_PROPS} aria-hidden>
        <circle cx="11" cy="11" r="7" />
        <path d="M21 21l-4.3-4.3" />
      </svg>
    ),
  },
  reviewing: {
    title: 'Reading the listings',
    sub: 'Pulling out prices and condition, then ranking the real deals.',
    steps: ['Extracting price & condition', 'Scoring each listing', 'Ranking the best deals'],
    icon: (
      <svg {...ICON_PROPS} aria-hidden>
        <path d="M4 6h16M4 12h16M4 18h10" />
      </svg>
    ),
  },
  negotiating: {
    title: 'Negotiating the price',
    sub: 'Making a strategic offer and reading the seller’s reply.',
    steps: ['Drafting an offer', 'Sending to the seller', 'Reading the reply'],
    icon: (
      <svg {...ICON_PROPS} aria-hidden>
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  awaiting_seller: {
    title: 'Waiting for the seller to respond…',
    sub: 'Your offer is with the seller. As soon as they reply, we’ll notify you on Telegram — you can safely leave this page and come back.',
    steps: ['Offer delivered', 'Waiting for the seller', 'We’ll ping you on Telegram'],
    icon: (
      <svg {...ICON_PROPS} aria-hidden>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
      </svg>
    ),
  },
  coordinating: {
    title: 'Arranging the meetup',
    sub: 'Finding a convenient public spot and a time that works for both.',
    steps: ['Locating a meeting point', 'Estimating travel time', 'Proposing a time'],
    icon: (
      <svg {...ICON_PROPS} aria-hidden>
        <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
        <circle cx="12" cy="10" r="3" />
      </svg>
    ),
  },
}

const FALLBACK: Phase = {
  title: 'Working on it',
  sub: 'The agents are on the task.',
  steps: ['Processing'],
  icon: (
    <svg {...ICON_PROPS} aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>
  ),
}

export default function ProcessingScreen({ status }: { status?: string }) {
  const phase = (status && PHASES[status]) || FALLBACK
  const [stepIdx, setStepIdx] = useState(0)

  // Advance the honest sub-step ticker; reset whenever the phase changes.
  useEffect(() => {
    setStepIdx(0)
    const id = setInterval(() => {
      setStepIdx((i) => Math.min(i + 1, phase.steps.length - 1))
    }, 1700)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  return (
    <main className="relative min-h-dvh overflow-hidden bg-[var(--color-bg)] px-5 py-10 sm:px-6">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 opacity-70"
        style={{
          background:
            'radial-gradient(60% 120% at 50% 0%, oklch(0.54 0.165 150 / 0.16), transparent 70%)',
        }}
      />

      <div className="console-rise relative mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-[34rem] flex-col lg:max-w-[44rem]">
        {/* Journey rail */}
        <StepBar status={status} />

        {/* Active-phase focus */}
        <div
          className="flex flex-1 flex-col items-center justify-center text-center"
          role="status"
          aria-live="polite"
        >
          {/* Phase glyph with breathing halo */}
          <div className="relative mb-8 grid h-20 w-20 place-items-center">
            <span
              aria-hidden
              className="breathe absolute inset-0 rounded-full bg-[var(--color-primary)] opacity-20 blur-md"
            />
            <span
              aria-hidden
              className="absolute inset-0 animate-ping rounded-full border border-[var(--color-primary)] opacity-20"
            />
            <span className="relative grid h-16 w-16 place-items-center rounded-full bg-[var(--color-surface)] text-[var(--color-primary)] ring-1 ring-[var(--color-border)]">
              {phase.icon}
            </span>
          </div>

          <h1 className="text-balance text-2xl font-bold tracking-[-0.01em] text-[var(--color-ink)]">
            {phase.title}
          </h1>
          <p className="mt-2 max-w-[40ch] text-pretty text-base leading-relaxed text-[var(--color-ink-muted)]">
            {phase.sub}
          </p>

          {/* Indeterminate sweep — proves work is in flight */}
          <div className="mt-8 h-1 w-full max-w-xs overflow-hidden rounded-full bg-[var(--color-surface-raised)]">
            <div className="indeterminate-bar h-full w-2/5 rounded-full bg-[var(--color-primary)]" />
          </div>

          {/* Honest sub-step ticker */}
          <ul className="mt-7 space-y-2.5 text-left">
            {phase.steps.map((s, i) => {
              const isDone = i < stepIdx
              const isActive = i === stepIdx
              return (
                <li key={s} className="flex items-center gap-2.5 text-sm">
                  <span className="grid h-4 w-4 shrink-0 place-items-center">
                    {isDone ? (
                      <svg viewBox="0 0 24 24" className="h-4 w-4 text-[var(--color-primary)]" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                        <path d="M5 13l4 4L19 7" />
                      </svg>
                    ) : isActive ? (
                      <span className="relative flex h-2 w-2">
                        <span aria-hidden className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--color-primary)] opacity-75" />
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--color-primary)]" />
                      </span>
                    ) : (
                      <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-border)]" />
                    )}
                  </span>
                  <span
                    className={
                      isActive
                        ? 'font-medium text-[var(--color-ink)]'
                        : isDone
                          ? 'text-[var(--color-ink-muted)]'
                          : 'text-[var(--color-ink-faint)]'
                    }
                  >
                    {s}
                  </span>
                </li>
              )
            })}
          </ul>
        </div>

        <p className="text-center text-xs text-[var(--color-ink-faint)]">
          You’ll be asked to decide when it matters.
        </p>
      </div>
    </main>
  )
}
