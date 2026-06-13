import { useState } from 'react'
import type { SessionState } from '../api'

export default function DoneScreen({ state }: { state: SessionState }) {
  const p = state.meetup_proposal
  const [copied, setCopied] = useState(false)

  const agreed = p?.final_price ?? state.final_price
  const chosen = state.ranked_candidates?.[state.current_candidate_index ?? 0]
  const savings =
    chosen?.price_eur != null && agreed != null && chosen.price_eur > agreed
      ? chosen.price_eur - agreed
      : null

  const handleCopy = async () => {
    const lines = [
      'BuyBot meetup',
      chosen?.title && `Item: ${chosen.title}`,
      p?.location && `Where: ${p.location}`,
      p?.time_suggestion && `When: ${p.time_suggestion}`,
      agreed != null && `Price agreed: €${agreed}`,
      p?.buyer_route?.duration_text && `Travel: ${p.buyer_route.duration_text}`,
    ].filter(Boolean) as string[]
    try {
      await navigator.clipboard.writeText(lines.join('\n'))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard unavailable — no-op */
    }
  }

  const Detail = ({ icon, label, value, accent }: { icon: React.ReactNode; label: string; value?: string; accent?: boolean }) =>
    value ? (
      <div className="flex items-center gap-3 px-4 py-3.5">
        <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg ${accent ? 'bg-[var(--color-accent)] text-[var(--color-accent-text)]' : 'bg-[var(--color-surface-raised)] text-[var(--color-ink-muted)]'}`}>
          {icon}
        </span>
        <div className="min-w-0 text-left">
          <p className={`text-xs ${accent ? 'text-[var(--color-accent)]' : 'text-[var(--color-ink-muted)]'}`}>{label}</p>
          <p className="truncate text-sm font-semibold text-[var(--color-ink)]">{value}</p>
        </div>
      </div>
    ) : null

  return (
    <main className="relative grid min-h-dvh place-items-center overflow-hidden bg-[var(--color-bg)] px-5 py-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-80 opacity-80"
        style={{
          background:
            'radial-gradient(55% 110% at 50% 0%, oklch(0.54 0.165 150 / 0.22), transparent 70%)',
        }}
      />

      <div className="console-rise relative w-full max-w-[30rem]">
        {/* Success glyph */}
        <div className="mx-auto mb-7 grid h-20 w-20 place-items-center">
          <span aria-hidden className="absolute h-20 w-20 rounded-full bg-[var(--color-primary)] opacity-20 blur-lg" />
          <span className="relative grid h-16 w-16 place-items-center rounded-full bg-[var(--color-primary)] text-[var(--color-primary-text)]">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M5 13l4 4L19 7" />
            </svg>
          </span>
        </div>

        <h1 className="text-balance text-center text-3xl font-bold tracking-[-0.02em] text-[var(--color-ink)]">
          The deal’s done
        </h1>
        <p className="mx-auto mt-3 max-w-[34ch] text-pretty text-center text-base leading-relaxed text-[var(--color-ink-muted)]">
          BuyBot searched, negotiated and set up the meetup.
          {savings != null ? ` It talked the seller down €${savings} — all you do is show up.` : ' All you do is show up.'}
        </p>

        {/* Locked-in details */}
        <div className="mt-7 divide-y divide-[var(--color-border)] overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]">
          {chosen?.title && (
            <Detail
              label="Item"
              value={chosen.title}
              icon={
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <rect x="5" y="2" width="14" height="20" rx="2.5" />
                  <path d="M11 18h2" />
                </svg>
              }
            />
          )}
          <Detail
            label="Where"
            value={p?.location}
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
            }
          />
          <Detail
            label="When"
            value={p?.time_suggestion}
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 2" />
              </svg>
            }
          />
          <Detail
            label="Bring (agreed price)"
            value={agreed != null ? `€${agreed} in cash` : undefined}
            accent
            icon={<span className="text-sm font-bold">€</span>}
          />
        </div>

        {/* Actions */}
        <div className="mt-6 flex flex-col gap-2.5 sm:flex-row">
          <button
            type="button"
            onClick={() => (window.location.href = '/')}
            className="order-2 flex-1 rounded-xl bg-[var(--color-primary)] py-3.5 text-sm font-semibold text-[var(--color-primary-text)] transition-[filter] duration-150 hover:brightness-110 active:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] sm:order-1"
          >
            Start a new search
          </button>
          <button
            type="button"
            onClick={handleCopy}
            aria-live="polite"
            className="order-1 inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--color-surface-raised)] px-5 py-3.5 text-sm font-medium text-[var(--color-ink)] transition-colors duration-150 hover:text-[var(--color-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border)] sm:order-2"
          >
            {copied ? (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M5 13l4 4L19 7" />
                </svg>
                Copied
              </>
            ) : (
              'Copy details'
            )}
          </button>
        </div>
      </div>
    </main>
  )
}
