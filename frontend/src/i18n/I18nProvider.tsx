import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { STRINGS, type Lang, type StringKey } from './strings'

interface I18nValue {
  lang: Lang
  setLang: (l: Lang) => void
  t: (key: StringKey) => string
}

const I18nContext = createContext<I18nValue | null>(null)
const STORAGE_KEY = 'envoy.lang'

function initialLang(): Lang {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'en' || saved === 'de') return saved
  return 'en' // onboarding default is English
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang)

  const setLang = useCallback((l: Lang) => {
    setLangState(l)
    localStorage.setItem(STORAGE_KEY, l)
  }, [])

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  const t = useCallback(
    (key: StringKey) => STRINGS[key]?.[lang] ?? STRINGS[key]?.en ?? key,
    [lang],
  )

  return <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}
