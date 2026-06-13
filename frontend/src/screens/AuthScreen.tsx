import { useState } from 'react'
import { useAuth } from '../auth/AuthProvider'
import { useI18n } from '../i18n/I18nProvider'
import LanguageSwitcher from '../components/LanguageSwitcher'

export default function AuthScreen() {
  const { t } = useI18n()
  const { login, signup } = useAuth()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isSignup = mode === 'signup'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (loading) return
    setLoading(true)
    setError(null)
    try {
      if (isSignup) await signup(email.trim(), password, name.trim())
      else await login(email.trim(), password)
      // On success the App.tsx gate swaps to the app automatically.
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
      setLoading(false)
    }
  }

  const inputClass =
    'w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-3 px-4 text-base text-[var(--color-ink)] placeholder:text-[var(--color-ink-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]'

  return (
    <main className="relative min-h-dvh overflow-hidden bg-[var(--color-bg)] px-5 py-10 sm:px-6">
      {/* Ambient system glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 opacity-70"
        style={{
          background:
            'radial-gradient(60% 120% at 50% 0%, oklch(0.62 0.165 150 / 0.16), transparent 70%)',
        }}
      />

      <div className="console-rise relative mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-[26rem] flex-col">
        {/* Brand + language */}
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
          <LanguageSwitcher />
        </header>

        {/* Form region */}
        <div className="flex flex-1 flex-col justify-center">
          <h1 className="text-balance text-[2rem] font-bold leading-[1.1] tracking-[-0.02em] text-[var(--color-ink)]">
            {isSignup ? t('auth.signup') : t('auth.login')}
          </h1>

          <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">
            {isSignup && (
              <div>
                <label htmlFor="name" className="mb-2 block text-sm font-medium text-[var(--color-ink)]">
                  {t('auth.name')}
                </label>
                <input
                  id="name"
                  type="text"
                  autoComplete="name"
                  className={inputClass}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
            )}

            <div>
              <label htmlFor="email" className="mb-2 block text-sm font-medium text-[var(--color-ink)]">
                {t('auth.email')}
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                className={inputClass}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-2 block text-sm font-medium text-[var(--color-ink)]">
                {t('auth.password')}
              </label>
              <input
                id="password"
                type="password"
                autoComplete={isSignup ? 'new-password' : 'current-password'}
                className={inputClass}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <p
                role="alert"
                className="rounded-lg bg-[var(--color-danger-dim)] px-4 py-3 text-sm text-[var(--color-ink)]"
              >
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-[var(--color-primary)] py-4 text-base font-semibold text-[var(--color-primary-text)] transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.99] active:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100 disabled:active:scale-100"
            >
              {loading ? (
                <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.3" />
                  <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                </svg>
              ) : isSignup ? (
                t('auth.signup')
              ) : (
                t('auth.login')
              )}
            </button>
          </form>

          {/* Mode toggle */}
          <button
            type="button"
            onClick={() => {
              setMode(isSignup ? 'login' : 'signup')
              setError(null)
            }}
            className="mt-6 cursor-pointer text-center text-sm text-[var(--color-ink-muted)] transition-colors hover:text-[var(--color-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
          >
            {isSignup ? (
              <>
                Have an account?{' '}
                <span className="font-semibold text-[var(--color-primary)]">{t('auth.login')}</span>
              </>
            ) : (
              <>
                No account?{' '}
                <span className="font-semibold text-[var(--color-primary)]">{t('auth.signup')}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </main>
  )
}
