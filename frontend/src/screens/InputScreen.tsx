import { useState } from 'react'
import { createSession } from '../api'
import { useI18n } from '../i18n/I18nProvider'
import LanguageSwitcher from '../components/LanguageSwitcher'

interface Props {
  onStart: (sessionId: string) => void
}

const CONDITIONS: { value: string; label: string }[] = [
  { value: 'acceptable', label: 'Acceptable' },
  { value: 'good', label: 'Good' },
  { value: 'good+', label: 'Good+' },
  { value: 'very_good', label: 'Very good' },
  { value: 'like_new', label: 'Like new' },
]

const AGENTS = ['Search', 'Extract', 'Analyst', 'Negotiate', 'Coordinate']

export default function InputScreen({ onStart }: Props) {
  const { t } = useI18n()
  const [query, setQuery] = useState('')
  const [budget, setBudget] = useState(200)
  const [condition, setCondition] = useState('good+')
  const [location, setLocation] = useState('München')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = query.trim().length > 0 && !loading

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading) return
    setLoading(true)
    setError(null)
    try {
      const id = await createSession({
        query: query.trim(),
        budget,
        condition,
        location: location.trim() || 'München',
        max_distance_km: 15,
      })
      onStart(id)
    } catch {
      setError("Couldn't reach the agents. Check the connection and try again.")
      setLoading(false)
    }
  }

  // Slider fill percentage for the track gradient
  const pct = ((budget - 50) / (2000 - 50)) * 100

  return (
    <main className="relative min-h-dvh overflow-hidden bg-[var(--color-bg)] px-5 py-10 sm:px-6">
      {/* Ambient system glow — signals the agents are powered and waiting */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 opacity-70"
        style={{
          background:
            'radial-gradient(60% 120% at 50% 0%, oklch(0.62 0.165 150 / 0.16), transparent 70%)',
        }}
      />

      <div className="console-rise relative mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-[34rem] flex-col lg:max-w-[40rem]">
        {/* Brand + readiness */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span
              aria-hidden
              className="grid h-7 w-7 place-items-center rounded-lg bg-[var(--color-primary)] text-[var(--color-primary-text)]"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 13l4 4L19 7" />
              </svg>
            </span>
            <span className="text-[1.0625rem] font-bold tracking-tight text-[var(--color-ink)]">
              BuyBot
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-ink-muted)]">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--color-primary)] opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[var(--color-primary)]" />
              </span>
              Agents ready
            </span>
            <LanguageSwitcher />
          </div>
        </header>

        {/* Heading */}
        <div className="mt-12">
          <h1
            className="text-balance text-[2rem] font-bold leading-[1.1] tracking-[-0.02em] text-[var(--color-ink)] sm:text-4xl"
          >
            {t('input.heading')}
          </h1>
          <p className="mt-3 max-w-[42ch] text-pretty text-base leading-relaxed text-[var(--color-ink-muted)]">
            Name one thing and a budget. My agents search every marketplace,
            rank the real deals, negotiate, and set up the meetup — you make
            three calls.
          </p>
        </div>

        {/* Command form */}
        <form onSubmit={handleSubmit} className="mt-9 flex flex-1 flex-col">
          {/* Query — the hero command */}
          <div>
            <label
              htmlFor="query"
              className="mb-2 block text-sm font-medium text-[var(--color-ink)]"
            >
              {t('input.item')}
            </label>
            <div className="relative">
              <span aria-hidden className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-ink-muted)]">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="7" />
                  <path d="M21 21l-4.3-4.3" />
                </svg>
              </span>
              <input
                id="query"
                autoFocus
                autoComplete="off"
                className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-4 pl-12 pr-4 text-lg text-[var(--color-ink)] placeholder:text-[var(--color-ink-muted)] transition-shadow duration-150 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                placeholder="iPhone 14, Sony A7 III, Eames chair…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>

          {/* Budget */}
          <div className="mt-7">
            <div className="mb-3 flex items-baseline justify-between">
              <label htmlFor="budget" className="text-sm font-medium text-[var(--color-ink)]">
                {t('input.budget')}
              </label>
              <span className="text-2xl font-bold tabular-nums text-[var(--color-ink)]">
                €{budget}
              </span>
            </div>
            <input
              id="budget"
              type="range"
              min={50}
              max={2000}
              step={10}
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className="range-primary"
              style={{
                background: `linear-gradient(to right, var(--color-primary) ${pct}%, var(--color-surface-raised) ${pct}%)`,
              }}
              aria-valuetext={`€${budget}`}
            />
            <div className="mt-1.5 flex justify-between text-xs tabular-nums text-[var(--color-ink-faint)]">
              <span>€50</span>
              <span>€2000</span>
            </div>
          </div>

          {/* Condition — ordinal segmented pills */}
          <fieldset className="mt-7">
            <legend className="mb-2.5 text-sm font-medium text-[var(--color-ink)]">
              {t('input.condition')}
            </legend>
            <div role="radiogroup" className="flex flex-wrap gap-2">
              {CONDITIONS.map((c) => {
                const active = condition === c.value
                return (
                  <button
                    key={c.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setCondition(c.value)}
                    className={`cursor-pointer rounded-lg px-3.5 py-2 text-sm font-medium transition-[background-color,color,transform] duration-150 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] ${
                      active
                        ? 'bg-[var(--color-primary)] text-[var(--color-primary-text)]'
                        : 'bg-[var(--color-surface-raised)] text-[var(--color-ink-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-ink)]'
                    }`}
                  >
                    {c.label}
                  </button>
                )
              })}
            </div>
          </fieldset>

          {/* Location */}
          <div className="mt-7">
            <label htmlFor="location" className="mb-2 block text-sm font-medium text-[var(--color-ink)]">
              {t('input.city')}
            </label>
            <div className="relative">
              <span aria-hidden className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-ink-muted)]">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
              </span>
              <input
                id="location"
                autoComplete="off"
                className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-3 pl-11 pr-4 text-base text-[var(--color-ink)] placeholder:text-[var(--color-ink-muted)] transition-shadow duration-150 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
          </div>

          {/* Error */}
          {error && (
            <p
              role="alert"
              className="mt-5 rounded-lg bg-[var(--color-danger-dim)] px-4 py-3 text-sm text-[var(--color-ink)]"
            >
              {error}
            </p>
          )}

          {/* Spacer pushes CTA + roster to the bottom on tall screens */}
          <div className="flex-1" />

          {/* Launch */}
          <button
            type="submit"
            disabled={!canSubmit}
            className="mt-8 flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-[var(--color-primary)] py-4 text-base font-semibold text-[var(--color-primary-text)] transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.99] active:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100 disabled:active:scale-100"
          >
            {loading ? (
              <>
                <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.3" />
                  <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                </svg>
                Dispatching agents…
              </>
            ) : (
              <>
                {t('input.submit')}
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
              </>
            )}
          </button>

          {/* Dormant agent roster — previews the system that's about to run */}
          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-2 gap-y-1.5 text-xs text-[var(--color-ink-faint)]">
            <span className="font-medium text-[var(--color-ink-muted)]">5 agents standing by</span>
            <span aria-hidden>·</span>
            {AGENTS.map((a, i) => (
              <span key={a} className="flex items-center gap-1">
                {i > 0 && <span aria-hidden className="text-[var(--color-border)]">/</span>}
                {a}
              </span>
            ))}
          </div>
        </form>
      </div>
    </main>
  )
}
