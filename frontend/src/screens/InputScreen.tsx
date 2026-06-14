import { useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { createSession, visionSearch, reverseGeocode } from '../api'
import type { VisionSearchResult } from '../api'
import { useI18n } from '../i18n/I18nProvider'
import { useAuth } from '../auth/AuthProvider'
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
  const { t, lang } = useI18n()
  const { user } = useAuth()
  const [query, setQuery] = useState('')
  const [budgetMin, setBudgetMin] = useState(50)
  const [budgetMax, setBudgetMax] = useState(200)
  const [condition, setCondition] = useState('good+')
  const [location, setLocation] = useState(user?.default_address || 'München')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [identifying, setIdentifying] = useState(false)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [matchedListing, setMatchedListing] = useState<VisionSearchResult['matched_listing']>(null)
  const [locating, setLocating] = useState(false)
  const [locationHint, setLocationHint] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const canSubmit = query.trim().length > 0 && !loading && !identifying

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading || identifying) return
    setLoading(true)
    setError(null)
    try {
      const id = await createSession({
        query: query.trim(),
        budget_min: budgetMin,
        budget_max: budgetMax,
        condition,
        location: location.trim() || 'München',
        max_distance_km: 15,
        language: lang,
      })
      onStart(id)
    } catch {
      setError("Couldn't reach the agents. Check the connection and try again.")
      setLoading(false)
    }
  }

  const handleImageSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFile(file)
    }
    // Reset so selecting the same file again re-triggers onChange
    e.target.value = ''
  }

  const handleFile = (file: File) => {
    setError(null)
    setMatchedListing(null)
    const reader = new FileReader()
    reader.onload = async () => {
      const dataUrl = reader.result as string
      setImagePreview(dataUrl)
      setIdentifying(true)
      try {
        // The endpoint accepts a full data URL; it returns a query plus an
        // optional seeded listing match.
        const result = await visionSearch(dataUrl)
        if (result.query) setQuery(result.query)
        setMatchedListing(result.matched_listing)
      } catch {
        // Non-fatal: leave the query field for manual entry.
        setError('Could not identify the image. Try another photo or type your item.')
      } finally {
        setIdentifying(false)
      }
    }
    reader.onerror = () => {
      setError('Could not read that image file.')
    }
    reader.readAsDataURL(file)
  }

  const clearImage = () => {
    setImagePreview(null)
    setMatchedListing(null)
  }

  const handleLocate = () => {
    setError(null)
    setLocationHint(null)
    if (!navigator.geolocation) {
      setError("Couldn't get your location — enter your city manually.")
      return
    }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords
        try {
          // Resolve coordinates to a human-readable place name.
          const place = await reverseGeocode(latitude, longitude)
          setLocation(place || `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`)
          setLocationHint(place ? `Using ${place}` : 'Using current location')
        } catch {
          setLocation(`${latitude.toFixed(4)}, ${longitude.toFixed(4)}`)
          setLocationHint('Using current location')
        } finally {
          setLocating(false)
        }
      },
      () => {
        setError("Couldn't get your location — enter your city manually.")
        setLocating(false)
      }
    )
  }

  // Slider fill percentages for the track gradients
  const pctMin = ((budgetMin - 50) / (2000 - 50)) * 100
  const pctMax = ((budgetMax - 50) / (2000 - 50)) * 100

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
              Envoy
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

            {/* Image upload — a subordinate way to fill the query from a photo */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleImageSelect}
            />
            <div className="mt-2.5 flex items-center gap-3">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={identifying}
                className="flex cursor-pointer items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-[var(--color-ink-muted)] transition-colors hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <path d="M21 15l-5-5L5 21" />
                </svg>
                Upload a photo
              </button>

              {identifying && (
                <span className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-ink-muted)]">
                  <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
                    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.3" />
                    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                  Identifying…
                </span>
              )}

              {imagePreview && (
                <span className="relative inline-block">
                  <img
                    src={imagePreview}
                    alt="Uploaded item"
                    className="h-10 w-10 rounded-lg object-cover ring-1 ring-[var(--color-border)]"
                  />
                  <button
                    type="button"
                    aria-label="Remove image"
                    onClick={clearImage}
                    className="absolute -right-1.5 -top-1.5 grid h-4 w-4 cursor-pointer place-items-center rounded-full bg-[var(--color-ink)] text-[var(--color-bg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
                  >
                    <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" aria-hidden>
                      <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              )}
            </div>

            {/* Seeded match — confirms the photo resolved to a real listing */}
            {matchedListing && (
              <div className="mt-2.5 inline-flex max-w-full items-center gap-1.5 rounded-lg border border-[var(--color-primary)]/40 bg-[var(--color-primary)]/10 px-2.5 py-1.5 text-xs font-medium text-[var(--color-ink)]">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M5 13l4 4L19 7" />
                </svg>
                <span className="truncate">
                  Matched: {matchedListing.title}
                  {matchedListing.price_text ? ` · ${matchedListing.price_text}` : ''}
                </span>
              </div>
            )}
          </div>

          {/* Budget range */}
          <div className="mt-7">
            <div className="mb-3 flex items-baseline justify-between">
              <label htmlFor="budget-min" className="text-sm font-medium text-[var(--color-ink)]">
                {t('input.budget')}
              </label>
              <span className="text-2xl font-bold tabular-nums text-[var(--color-ink)]">
                €{budgetMin} – €{budgetMax}
              </span>
            </div>

            <label htmlFor="budget-min" className="mb-1.5 block text-xs font-medium text-[var(--color-ink-muted)]">
              Min budget
            </label>
            <input
              id="budget-min"
              type="range"
              min={50}
              max={2000}
              step={10}
              value={budgetMin}
              onChange={(e) => setBudgetMin(Math.min(Number(e.target.value), budgetMax))}
              className="range-primary"
              style={{
                background: `linear-gradient(to right, var(--color-primary) ${pctMin}%, var(--color-surface-raised) ${pctMin}%)`,
              }}
              aria-valuetext={`€${budgetMin}`}
            />

            <label htmlFor="budget-max" className="mb-1.5 mt-4 block text-xs font-medium text-[var(--color-ink-muted)]">
              Max budget
            </label>
            <input
              id="budget-max"
              type="range"
              min={50}
              max={2000}
              step={10}
              value={budgetMax}
              onChange={(e) => setBudgetMax(Math.max(Number(e.target.value), budgetMin))}
              className="range-primary"
              style={{
                background: `linear-gradient(to right, var(--color-primary) ${pctMax}%, var(--color-surface-raised) ${pctMax}%)`,
              }}
              aria-valuetext={`€${budgetMax}`}
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
                className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-3 pl-11 pr-14 text-base text-[var(--color-ink)] placeholder:text-[var(--color-ink-muted)] transition-shadow duration-150 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                value={location}
                onChange={(e) => { setLocation(e.target.value); setLocationHint(null) }}
              />
              <button
                type="button"
                aria-label="Use my location"
                onClick={handleLocate}
                disabled={locating}
                className="absolute right-2 top-1/2 grid h-9 w-9 -translate-y-1/2 cursor-pointer place-items-center rounded-lg text-[var(--color-ink-muted)] transition-colors hover:bg-[var(--color-surface)] hover:text-[var(--color-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {locating ? (
                  <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.3" />
                    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <circle cx="12" cy="12" r="3" />
                    <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
                  </svg>
                )}
              </button>
            </div>
            {locationHint && (
              <p className="mt-1.5 text-xs font-medium text-[var(--color-ink-muted)]">{locationHint}</p>
            )}
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
