import { useState, useEffect } from 'react'
import { translateText } from '../api'

const _cache = new Map<string, string>() // key: `${lang}|${text}`

export function useMessageTranslation(text: string, targetLang: string, enabled: boolean) {
  const key = `${targetLang}|${text}`
  const [translation, setTranslation] = useState<string>(() => _cache.get(key) ?? '')

  useEffect(() => {
    if (!enabled || !text.trim()) return
    if (_cache.has(key)) {
      setTranslation(_cache.get(key)!)
      return
    }
    let cancelled = false
    translateText(text, targetLang).then((res) => {
      if (cancelled) return
      _cache.set(key, res)
      setTranslation(res)
    })
    return () => {
      cancelled = true
    }
  }, [key, text, targetLang, enabled])

  return translation
}
