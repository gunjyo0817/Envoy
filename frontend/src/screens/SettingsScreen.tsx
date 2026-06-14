import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSettings, updateSettings, calendarStatus, calendarAuthUrl, telegramStatus, telegramLinkToken } from '../api'
import { useI18n } from '../i18n/I18nProvider'
import { useAuth } from '../auth/AuthProvider'
import { LANGS, type Lang } from '../i18n/strings'

export default function SettingsScreen() {
  const { t, setLang } = useI18n()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [language, setLanguage] = useState<string>('en')
  const [defaultAddress, setDefaultAddress] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [calConnected, setCalConnected] = useState<boolean | null>(null)
  const [tgConnected, setTgConnected] = useState<boolean | null>(null)
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // No session (logged out, or token invalidated by a backend restart) →
  // bounce to the buyer flow, which renders the auth screen.
  useEffect(() => {
    if (!user) navigate('/')
  }, [user, navigate])

  useEffect(() => {
    if (!user) return
    let active = true
    getSettings()
      .then((s) => {
        if (!active) return
        setLanguage(s.language)
        setDefaultAddress(s.default_address)
      })
      .catch(() => {
        if (!active) return
        // Most likely an expired/invalid token → drop the session and re-auth.
        logout()
        navigate('/')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [user, logout, navigate])

  useEffect(() => {
    if (!user) return
    calendarStatus().then((s) => setCalConnected(s.connected)).catch(() => setCalConnected(false))
  }, [user])

  useEffect(() => {
    if (!user) return
    telegramStatus().then((s) => setTgConnected(s.connected)).catch(() => setTgConnected(false))
  }, [user])

  useEffect(() => {
    return () => {
      if (savedTimer.current) clearTimeout(savedTimer.current)
    }
  }, [])

  const connectCalendar = async () => {
    window.location.href = await calendarAuthUrl()
  }

  const connectTelegram = async () => {
    const { url } = await telegramLinkToken()
    if (url) window.open(url, '_blank', 'noopener')
  }

  const handleLangChange = (l: Lang) => {
    setLanguage(l)
    setLang(l) // live-update the UI immediately + persist to localStorage
  }

  const handleSave = async () => {
    if (saving) return
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      await updateSettings({ language, default_address: defaultAddress })
      setSaved(true)
      if (savedTimer.current) clearTimeout(savedTimer.current)
      savedTimer.current = setTimeout(() => setSaved(false), 2000)
    } catch {
      setError('Could not save your settings. Try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <main className="relative min-h-dvh overflow-hidden bg-[var(--color-bg)] px-5 py-10 sm:px-6">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 opacity-70"
        style={{
          background:
            'radial-gradient(60% 120% at 50% 0%, oklch(0.62 0.165 150 / 0.16), transparent 70%)',
        }}
      />

      <div className="console-rise relative mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-[34rem] flex-col">
        {/* Title */}
        <div className="mt-10">
          <h1 className="text-[2rem] font-bold leading-[1.1] tracking-[-0.02em] text-[var(--color-ink)]">
            {t('settings.title')}
          </h1>
          {user?.email && (
            <p className="mt-2 text-sm text-[var(--color-ink-muted)]">{user.email}</p>
          )}
        </div>

        {loading ? (
          <div className="mt-12 flex items-center gap-2 text-sm text-[var(--color-ink-muted)]">
            <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.3" />
              <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
            {t('common.loading')}
          </div>
        ) : (
          <div className="mt-9 flex flex-1 flex-col">
            {/* Language */}
            <div>
              <label htmlFor="language" className="mb-2 block text-sm font-medium text-[var(--color-ink)]">
                {t('settings.language')}
              </label>
              <select
                id="language"
                value={language}
                onChange={(e) => handleLangChange(e.target.value as Lang)}
                className="w-full cursor-pointer rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-4 py-3 text-base text-[var(--color-ink)] transition-shadow duration-150 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              >
                {LANGS.map((l) => (
                  <option key={l.code} value={l.code}>{l.label}</option>
                ))}
              </select>
            </div>

            {/* Default address */}
            <div className="mt-7">
              <label htmlFor="default-address" className="mb-2 block text-sm font-medium text-[var(--color-ink)]">
                {t('settings.defaultAddress')}
              </label>
              <input
                id="default-address"
                autoComplete="off"
                value={defaultAddress}
                onChange={(e) => setDefaultAddress(e.target.value)}
                className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-3 px-4 text-base text-[var(--color-ink)] placeholder:text-[var(--color-ink-muted)] transition-shadow duration-150 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              />
            </div>

            {/* Telegram */}
            <div className="mt-7">
              <p className="mb-2 block text-sm font-medium text-[var(--color-ink)]">Telegram</p>
              {tgConnected ? (
                <p className="text-sm text-[var(--color-primary)]">Connected — you'll get negotiation pings in Telegram.</p>
              ) : (
                <button
                  type="button"
                  onClick={connectTelegram}
                  className="cursor-pointer rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-5 py-3 text-sm font-medium text-[var(--color-ink)] hover:bg-[var(--color-surface)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
                >
                  Connect Telegram
                </button>
              )}
            </div>

            {/* Google Calendar */}
            <div className="mt-7">
              <p className="mb-2 block text-sm font-medium text-[var(--color-ink)]">Google Calendar</p>
              {calConnected ? (
                <p className="text-sm text-[var(--color-primary)]">Connected — meetups can be added to your calendar.</p>
              ) : (
                <button
                  type="button"
                  onClick={connectCalendar}
                  className="cursor-pointer rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-5 py-3 text-sm font-medium text-[var(--color-ink)] hover:bg-[var(--color-surface)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
                >
                  Connect Google Calendar
                </button>
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

            {/* Save */}
            <div className="mt-7 flex items-center gap-3">
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-[var(--color-primary)] px-6 py-3 text-base font-semibold text-[var(--color-primary-text)] transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.99] active:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100"
              >
                {saving && (
                  <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
                    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.3" />
                    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                )}
                {t('settings.save')}
              </button>
              {saved && (
                <span role="status" className="text-sm font-medium text-[var(--color-accent)]">
                  Saved
                </span>
              )}
            </div>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Log out */}
            <button
              type="button"
              onClick={handleLogout}
              className="mt-8 w-full cursor-pointer rounded-xl bg-[var(--color-danger-dim)] py-3 text-sm font-semibold text-[var(--color-ink)] transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
            >
              Log out
            </button>
          </div>
        )}
      </div>
    </main>
  )
}
