import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listDeals, getDeal, type Deal } from '../api'
import NegotiationThread from '../components/NegotiationThread'

function StatusChip({ status }: { status: string }) {
  const done = status === 'done'
  return (
    <span
      className={[
        'rounded-full px-2.5 py-0.5 text-xs font-medium',
        done
          ? 'bg-[color-mix(in_oklch,var(--color-primary)_20%,transparent)] text-[var(--color-primary)]'
          : 'bg-[var(--color-surface-raised)] text-[var(--color-ink-muted)]',
      ].join(' ')}
    >
      {done ? 'Deal closed' : 'No deal'}
    </span>
  )
}

function BackButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mb-5 inline-flex cursor-pointer items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-[var(--color-ink-muted)] transition-colors hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M19 12H5M11 6l-6 6 6 6" />
      </svg>
      {label}
    </button>
  )
}

export default function HistoryScreen() {
  const navigate = useNavigate()
  const [deals, setDeals] = useState<Deal[] | null>(null)
  const [selected, setSelected] = useState<Deal | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listDeals().then(setDeals).catch(() => setError('Could not load history'))
  }, [])

  const open = async (sessionId: string) => {
    try {
      setSelected(await getDeal(sessionId))
    } catch {
      setError('Could not load deal')
    }
  }

  if (selected) {
    const m = selected.meetup as { location?: string; time_suggestion?: string }
    return (
      <main className="min-h-dvh bg-[var(--color-bg)] px-5 py-10 text-[var(--color-ink)] sm:px-6">
        <div className="console-rise mx-auto w-full max-w-[34rem] lg:max-w-[40rem]">
          <BackButton label="Back to history" onClick={() => setSelected(null)} />
          <h1 className="text-balance text-2xl font-bold tracking-[-0.02em] text-[var(--color-ink)]">
            {selected.query ?? 'Procurement'}
          </h1>
          <div className="mt-3 flex items-center gap-3">
            <StatusChip status={selected.status} />
            {selected.final_price != null && (
              <span className="tabular-nums text-sm font-medium text-[var(--color-ink-muted)]">
                €{selected.final_price}
              </span>
            )}
          </div>
          {m?.location && (
            <p className="mt-3 text-sm text-[var(--color-ink-muted)]">
              Meetup: {m.location}
              {m.time_suggestion ? ` · ${m.time_suggestion}` : ''}
            </p>
          )}
          <h2 className="mt-8 mb-3 text-sm font-medium text-[var(--color-ink-faint)]">Negotiation</h2>
          {selected.negotiation_thread.length ? (
            <NegotiationThread thread={selected.negotiation_thread} />
          ) : (
            <p className="text-sm text-[var(--color-ink-muted)]">No messages recorded.</p>
          )}
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-dvh bg-[var(--color-bg)] px-5 py-10 text-[var(--color-ink)] sm:px-6">
      <div className="console-rise mx-auto w-full max-w-[34rem] lg:max-w-[40rem]">
        <BackButton label="Home" onClick={() => navigate('/')} />
        <h1 className="text-balance text-2xl font-bold tracking-[-0.02em] text-[var(--color-ink)]">
          History
        </h1>
        <p className="mt-2 text-sm text-[var(--color-ink-muted)]">
          Past deals and the negotiations behind them.
        </p>

        {error && <p className="mt-5 text-sm text-[var(--color-danger)]">{error}</p>}
        {deals === null && !error && (
          <p className="mt-5 text-sm text-[var(--color-ink-muted)]">Loading…</p>
        )}
        {deals && deals.length === 0 && (
          <p className="mt-5 text-sm text-[var(--color-ink-muted)]">No past deals yet.</p>
        )}

        <ul className="mt-5 space-y-3">
          {deals?.map((d) => (
            <li key={d.session_id}>
              <button
                type="button"
                onClick={() => open(d.session_id)}
                className="flex w-full cursor-pointer items-center gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-left transition-colors hover:bg-[var(--color-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
              >
                {d.thumbnail ? (
                  <img src={d.thumbnail} alt="" className="h-12 w-12 shrink-0 rounded-lg object-cover" />
                ) : (
                  <div className="h-12 w-12 shrink-0 rounded-lg bg-[var(--color-surface-raised)]" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-[var(--color-ink)]">
                    {d.query ?? 'Procurement'}
                  </p>
                  <div className="mt-1.5 flex items-center gap-2">
                    <StatusChip status={d.status} />
                    {d.final_price != null && (
                      <span className="tabular-nums text-xs text-[var(--color-ink-muted)]">
                        €{d.final_price}
                      </span>
                    )}
                  </div>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden className="shrink-0 text-[var(--color-ink-faint)]">
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </main>
  )
}
