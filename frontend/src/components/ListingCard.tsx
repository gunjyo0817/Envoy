import type { Candidate } from '../api'

interface Props {
  candidate: Candidate
  rank: number
  variant?: 'full' | 'compact'
  onClick?: () => void
  selected?: boolean
  disabled?: boolean
}

// Shared interactive affordance applied when a card is clickable.
function interactiveProps(onClick?: () => void, disabled?: boolean) {
  if (!onClick) return {}
  return {
    role: 'button' as const,
    tabIndex: disabled ? -1 : 0,
    'aria-disabled': disabled || undefined,
    onClick: disabled ? undefined : onClick,
    onKeyDown: (e: React.KeyboardEvent) => {
      if (disabled) return
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        onClick()
      }
    },
  }
}

const CLICKABLE =
  'cursor-pointer transition hover:border-[var(--color-primary)] hover:-translate-y-0.5 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]'

const CONDITION_LABEL: Record<string, string> = {
  new: 'New',
  like_new: 'Like new',
  very_good: 'Very good',
  good: 'Good',
  acceptable: 'Acceptable',
}

const PLATFORM_LABEL: Record<string, string> = {
  kleinanzeigen: 'Kleinanzeigen',
  vinted: 'Vinted',
  facebook: 'Facebook',
}

function StarIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 2.5l2.9 5.9 6.5.95-4.7 4.58 1.1 6.47L12 17.9l-5.8 3.07 1.1-6.47L2.6 9.9l6.5-.95L12 2.5z" />
    </svg>
  )
}

function PinIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  )
}

export default function ListingCard({ candidate, rank, variant, onClick, selected, disabled }: Props) {
  const v = variant ?? (rank === 0 ? 'full' : 'compact')
  const condition = CONDITION_LABEL[candidate.condition] ?? candidate.condition
  const platform = PLATFORM_LABEL[candidate.platform] ?? candidate.platform
  const clickable = !!onClick
  const ring = selected ? ' ring-2 ring-[var(--color-primary)]' : ''
  const interactive = clickable ? ` ${CLICKABLE}${ring}` : ''

  if (v === 'compact') {
    return (
      <article
        {...interactiveProps(onClick, disabled)}
        className={`flex items-center gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3${clickable ? ` ${CLICKABLE}${ring} hover:bg-[var(--color-surface-raised)]` : ''}`}
      >
        <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[var(--color-surface-raised)] text-xs font-semibold text-[var(--color-ink-muted)]">
          {rank + 1}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-medium text-[var(--color-ink)]">{candidate.title}</h3>
          <p className="mt-0.5 truncate text-xs text-[var(--color-ink-muted)]">
            {condition} · {candidate.location}
          </p>
        </div>
        <span className="shrink-0 text-base font-bold tabular-nums text-[var(--color-ink)]">
          €{candidate.price_eur}
        </span>
      </article>
    )
  }

  return (
    <article
      {...interactiveProps(onClick, disabled)}
      className={`rounded-2xl border border-[var(--color-primary-dim)] bg-[var(--color-surface)] p-5${interactive}`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--color-primary)] px-2.5 py-1 text-xs font-semibold text-[var(--color-primary-text)]">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <path d="M5 13l4 4L19 7" />
          </svg>
          Top pick
        </span>
        <span className="text-xs font-medium text-[var(--color-ink-muted)]">{platform}</span>
      </div>

      <h3 className="mt-3 text-pretty text-lg font-semibold leading-snug text-[var(--color-ink)]">
        {candidate.title}
      </h3>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="text-3xl font-bold tabular-nums text-[var(--color-ink)]">
          €{candidate.price_eur}
        </span>
        {candidate.score >= 85 && (
          <span className="rounded-full bg-[var(--color-primary-dim)] px-2.5 py-0.5 text-xs font-semibold text-[var(--color-primary)]">
            Great value
          </span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-[var(--color-ink-muted)]">
        <span className="rounded-md bg-[var(--color-surface-raised)] px-2 py-0.5 text-xs font-medium text-[var(--color-ink)]">
          {condition}
        </span>
        {candidate.seller_rating != null && (
          <span className="inline-flex items-center gap-1">
            <span className="text-[var(--color-accent)]"><StarIcon /></span>
            {candidate.seller_rating}
            {candidate.seller_reviews != null && (
              <span className="text-[var(--color-ink-faint)]"> ({candidate.seller_reviews})</span>
            )}
          </span>
        )}
        <span className="inline-flex items-center gap-1">
          <PinIcon />
          {candidate.location}
        </span>
      </div>

      {candidate.insight && (
        <p className="mt-4 flex items-start gap-2 rounded-xl bg-[oklch(0.38_0.110_150_/_0.22)] px-3.5 py-2.5 text-sm leading-relaxed text-[var(--color-ink)]">
          <svg className="mt-0.5 shrink-0 text-[var(--color-primary)]" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.1h6c0-.8.4-1.6 1-2.1A7 7 0 0 0 12 2Z" />
          </svg>
          {candidate.insight}
        </p>
      )}
    </article>
  )
}
