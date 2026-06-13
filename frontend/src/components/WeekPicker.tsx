import { useEffect, useState } from 'react'
import { getFreebusy } from '../api'

const SLOTS = [{ label: 'Morning', h: 10 }, { label: 'Afternoon', h: 15 }, { label: 'Evening', h: 18 }]

function isBusy(d: Date, busy: { start: string; end: string }[]): boolean {
  const t = d.getTime()
  return busy.some((b) => t >= new Date(b.start).getTime() && t < new Date(b.end).getTime())
}

export default function WeekPicker({ onSend, onCancel }: { onSend: (slots: string[]) => void; onCancel: () => void }) {
  const [busy, setBusy] = useState<{ start: string; end: string }[]>([])
  const [picked, setPicked] = useState<string[]>([])
  const days = Array.from({ length: 7 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i + 1); return d })

  useEffect(() => {
    const from = new Date(); from.setHours(0, 0, 0, 0)
    const to = new Date(from); to.setDate(to.getDate() + 8)
    getFreebusy(from.toISOString(), to.toISOString()).then((r) => setBusy(r.busy)).catch(() => {})
  }, [])

  const toggle = (iso: string) => setPicked((p) =>
    p.includes(iso) ? p.filter((x) => x !== iso) : (p.length < 3 ? [...p, iso] : p))

  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <p className="mb-3 text-sm font-medium text-[var(--color-ink)]">Pick up to 3 times you're free</p>
      <div className="space-y-2">
        {days.map((day) => (
          <div key={day.toDateString()} className="flex items-center gap-2">
            <span className="w-10 shrink-0 text-xs text-[var(--color-ink-muted)]">
              {day.toLocaleDateString(undefined, { weekday: 'short' })}
            </span>
            {SLOTS.map((s) => {
              const d = new Date(day); d.setHours(s.h, 0, 0, 0)
              const iso = d.toISOString()
              const disabled = isBusy(d, busy)
              const on = picked.includes(iso)
              return (
                <button key={s.h} type="button" disabled={disabled} onClick={() => toggle(iso)}
                  className={[
                    'flex-1 rounded-lg px-2 py-2 text-xs font-medium',
                    disabled ? 'cursor-not-allowed bg-[var(--color-bg)] text-[var(--color-ink-faint)] line-through'
                      : on ? 'bg-[var(--color-primary)] text-[var(--color-primary-text)]'
                      : 'bg-[var(--color-surface-raised)] text-[var(--color-ink)] hover:brightness-110',
                  ].join(' ')}>
                  {s.label}
                </button>
              )
            })}
          </div>
        ))}
      </div>
      <div className="mt-4 flex gap-2">
        <button type="button" disabled={!picked.length} onClick={() => onSend(picked)}
          className="flex-1 rounded-xl bg-[var(--color-primary)] py-3 text-sm font-semibold text-[var(--color-primary-text)] disabled:opacity-40">
          Send {picked.length || ''} to seller
        </button>
        <button type="button" onClick={onCancel}
          className="rounded-xl bg-[var(--color-surface-raised)] px-5 py-3 text-sm text-[var(--color-ink)]">Cancel</button>
      </div>
    </div>
  )
}
