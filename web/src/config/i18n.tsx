import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import vi, { type LocaleKeys } from './locales/vi'
import en from './locales/en'

// ── Supported languages ──
export type Lang = 'vi' | 'en'

const LOCALES: Record<Lang, LocaleKeys> = { vi, en }

const STORAGE_KEY = 'app_language'

// ── Helper: get nested value by dot-notation key ──
function getNestedValue(obj: any, path: string): string {
  const keys = path.split('.')
  let current = obj
  for (const key of keys) {
    if (current == null || typeof current !== 'object') return path
    current = current[key]
  }
  return typeof current === 'string' ? current : path
}

// ── Context ──
interface LanguageContextType {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: string, params?: Record<string, string | number>) => string
}

const LanguageContext = createContext<LanguageContextType | null>(null)

// ── Provider ──
function getInitialLang(): Lang {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'en' || stored === 'vi') return stored
  } catch { /* SSR / private browsing */ }
  return 'vi' // default Vietnamese
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(getInitialLang)

  const setLang = useCallback((newLang: Lang) => {
    setLangState(newLang)
    try {
      localStorage.setItem(STORAGE_KEY, newLang)
    } catch { /* ignore */ }
  }, [])

  const t = useCallback((key: string, params?: Record<string, string | number>): string => {
    let val = getNestedValue(LOCALES[lang], key)
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        val = val.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
      })
    }
    return val
  }, [lang])

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

// ── Hook ──
export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) {
    // Fallback when used outside provider (shouldn't happen)
    return {
      lang: 'vi' as Lang,
      setLang: () => {},
      t: (key: string) => getNestedValue(vi, key),
    }
  }
  return ctx
}
