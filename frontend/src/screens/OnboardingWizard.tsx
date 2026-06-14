import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import {
  completeOnboarding, telegramLinkToken, telegramStatus, calendarAuthUrl,
} from '../api'

export default function OnboardingWizard() {
  const navigate = useNavigate()
  const { refreshUser } = useAuth()
  const [step, setStep] = useState(0) // 0 welcome, 1 telegram, 2 calendar
  const [tgUrl, setTgUrl] = useState<string | null>(null)
  const [tgConnected, setTgConnected] = useState(false)

  // Fetch the deep link when entering the Telegram step.
  useEffect(() => {
    if (step !== 1 || tgUrl) return
    telegramLinkToken().then((r) => setTgUrl(r.url)).catch(() => setTgUrl(''))
  }, [step, tgUrl])

  // Poll binding status while on the Telegram step.
  useEffect(() => {
    if (step !== 1 || tgConnected) return
    const id = setInterval(() => {
      telegramStatus().then((s) => { if (s.connected) setTgConnected(true) }).catch(() => {})
    }, 2500)
    return () => clearInterval(id)
  }, [step, tgConnected])

  const finish = async () => {
    try { await completeOnboarding(); await refreshUser() } catch { /* ignore */ }
    navigate('/search', { replace: true })
  }

  const connectCalendar = async () => {
    try { await completeOnboarding(); await refreshUser() } catch { /* ignore */ }
    window.location.href = await calendarAuthUrl()
  }

  const Dots = () => (
    <div className="flex gap-1.5">
      {[0, 1, 2].map((i) => (
        <span key={i} className={`h-1 w-6 rounded-full ${i <= step ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-border)]'}`} />
      ))}
    </div>
  )

  return (
    <main className="relative min-h-dvh overflow-hidden bg-[var(--color-bg)] px-5 py-10 sm:px-6">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 opacity-70"
        style={{ background: 'radial-gradient(60% 120% at 50% 0%, oklch(0.62 0.165 150 / 0.16), transparent 70%)' }}
      />
      <div className="console-rise relative mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-[26rem] flex-col">
        <header className="flex items-center justify-between">
          <Dots />
          {step > 0 && (
            <button type="button" onClick={finish}
              className="cursor-pointer text-sm font-medium text-[var(--color-ink-muted)] transition-colors hover:text-[var(--color-ink)]">
              Skip
            </button>
          )}
        </header>

        <div className="flex flex-1 flex-col justify-center">
          {step === 0 && (
            <>
              <div className="text-4xl">🤝</div>
              <h1 className="mt-4 text-[2rem] font-bold leading-[1.1] tracking-[-0.02em] text-[var(--color-ink)]">Welcome to Envoy</h1>
              <p className="mt-3 text-base leading-relaxed text-[var(--color-ink-muted)]">
                Your agent searches, negotiates, and books the meetup for second-hand buys. Let's set up notifications so it can reach you.
              </p>
            </>
          )}

          {step === 1 && (
            <>
              <h1 className="text-[2rem] font-bold leading-[1.1] tracking-[-0.02em] text-[var(--color-ink)]">Connect Telegram</h1>
              <p className="mt-3 text-base leading-relaxed text-[var(--color-ink-muted)]">
                Get live pings when the seller replies or a meetup is proposed — and approve right from chat.
              </p>
              <div className="mt-7 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-4">
                {tgConnected ? (
                  <p className="text-sm font-medium text-[var(--color-primary)]">✓ Telegram connected — pings enabled.</p>
                ) : (
                  <p className="text-sm text-[var(--color-ink-muted)]">⏳ Waiting for you to tap <strong className="text-[var(--color-ink)]">Start</strong> in the bot…</p>
                )}
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div className="text-4xl">📅</div>
              <h1 className="mt-4 text-[2rem] font-bold leading-[1.1] tracking-[-0.02em] text-[var(--color-ink)]">Add to your calendar?</h1>
              <p className="mt-3 text-base leading-relaxed text-[var(--color-ink-muted)]">
                Optional. Connect Google Calendar so confirmed meetups appear automatically, with travel time accounted for.
              </p>
            </>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-3">
          {step === 0 && (
            <button type="button" onClick={() => setStep(1)} className={primaryBtn}>Get started</button>
          )}
          {step === 1 && (
            <>
              {!tgConnected && tgUrl && (
                <a href={tgUrl} target="_blank" rel="noreferrer" className={primaryBtn}>Open Telegram</a>
              )}
              {!tgConnected && tgUrl === '' && (
                <p className="text-center text-sm text-[var(--color-ink-muted)]">Telegram isn't configured — you can skip this for now.</p>
              )}
              <button type="button" onClick={() => setStep(2)} className={tgConnected ? primaryBtn : ghostBtn}>
                {tgConnected ? 'Continue' : 'Next'}
              </button>
            </>
          )}
          {step === 2 && (
            <>
              <button type="button" onClick={connectCalendar} className={primaryBtn}>Connect Calendar</button>
              <button type="button" onClick={finish} className={ghostBtn}>Maybe later</button>
            </>
          )}
        </div>
      </div>
    </main>
  )
}

const primaryBtn =
  'flex w-full cursor-pointer items-center justify-center rounded-xl bg-[var(--color-primary)] py-4 text-base font-semibold text-[var(--color-primary-text)] transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]'
const ghostBtn =
  'flex w-full cursor-pointer items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-3.5 text-base font-medium text-[var(--color-ink)] transition hover:bg-[var(--color-surface)] active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]'
