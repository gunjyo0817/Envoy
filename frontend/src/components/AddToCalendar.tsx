import { useState } from 'react'
import { addCalendarEvent } from '../api'

function defaultStart(): string {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  d.setHours(15, 0, 0, 0)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function AddToCalendar({ summary, location }: { summary: string; location: string }) {
  const [when, setWhen] = useState(defaultStart())
  const [busy, setBusy] = useState(false)
  const [link, setLink] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const add = async () => {
    setBusy(true); setErr(null)
    try {
      const start = new Date(when)
      const end = new Date(start.getTime() + 30 * 60 * 1000)
      const res = await addCalendarEvent({
        summary, location, start_iso: start.toISOString(), end_iso: end.toISOString(),
      })
      setLink(res.htmlLink)
    } catch (e) {
      setErr((e as Error).message === 'not_connected'
        ? 'Connect Google Calendar in Settings first.' : 'Could not add to calendar.')
    } finally { setBusy(false) }
  }

  if (link) {
    return (
      <a href={link} target="_blank" rel="noreferrer"
        className="inline-flex items-center gap-2 text-sm font-medium text-[var(--color-primary)]">
        ✓ Added — view in Google Calendar
      </a>
    )
  }
  return (
    <div className="flex flex-col gap-2">
      <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)}
        className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-4 py-2.5 text-sm text-[var(--color-ink)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]" />
      <button type="button" onClick={add} disabled={busy}
        className="cursor-pointer rounded-xl bg-[var(--color-surface-raised)] px-5 py-3 text-sm font-medium text-[var(--color-ink)] hover:bg-[var(--color-surface)] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]">
        {busy ? 'Adding…' : 'Add to Google Calendar'}
      </button>
      {err && <p className="text-xs text-[var(--color-ink-muted)]">{err}</p>}
    </div>
  )
}
