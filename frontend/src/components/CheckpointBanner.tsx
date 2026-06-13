import type { PendingDecision } from '../api'

interface Props {
  decision: PendingDecision
  onChoice: (id: string) => void
  loading?: boolean
  /** Short amber eyebrow above the summary, e.g. "Your call". */
  eyebrow?: string
}

export default function CheckpointBanner({ decision, onChoice, loading, eyebrow = 'Your call' }: Props) {
  const primaryId = decision.options[0]?.id

  return (
    <section
      aria-label="Decision required"
      className="rounded-2xl border-t-2 border-[var(--color-accent)] bg-[oklch(0.14_0.025_60)] p-5"
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[var(--color-accent)] text-[var(--color-accent-text)]"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 8v5" />
            <circle cx="12" cy="16.5" r="0.6" fill="currentColor" stroke="none" />
          </svg>
        </span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-accent)]">
            {eyebrow}
          </p>
          <p className="mt-1 text-pretty text-[0.9375rem] font-medium leading-snug text-[var(--color-ink)]">
            {decision.summary}
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2.5">
        {decision.options.map((opt) => {
          const isPrimary = opt.id === primaryId
          return (
            <button
              key={opt.id}
              type="button"
              disabled={loading}
              onClick={() => onChoice(opt.id)}
              className={
                isPrimary
                  ? 'inline-flex items-center gap-2 rounded-xl bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-[var(--color-primary-text)] transition-[filter] duration-150 hover:brightness-110 active:brightness-95 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2 focus-visible:ring-offset-[oklch(0.14_0.025_60)]'
                  : 'inline-flex items-center rounded-xl bg-[var(--color-surface-raised)] px-4 py-3 text-sm font-medium text-[var(--color-ink-muted)] transition-colors duration-150 hover:text-[var(--color-ink)] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border)]'
              }
            >
              {isPrimary && loading && (
                <svg className="animate-spin" width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.3" />
                  <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                </svg>
              )}
              {opt.label}
            </button>
          )
        })}
      </div>
    </section>
  )
}
