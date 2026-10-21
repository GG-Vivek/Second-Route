/**
 * The theme provider (F8.1).
 *
 * The application ships dark by default and offers a light mode. The
 * choice is remembered, and the operating system can be followed instead.
 *
 * The class is put on the document element rather than on a wrapper, so
 * that the tokens apply to the portals the dialogs and the sheets render
 * into as well.
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  DARK_SCHEME_QUERY,
  ThemeContext,
  THEME_STORAGE_KEY,
  readStoredPreference,
  readSystemTheme,
  resolveTheme,
  writeStoredPreference,
  type ResolvedTheme,
  type ThemeContextValue,
  type ThemePreference,
} from './ThemeContext'

export interface ThemeProviderProps {
  children: ReactNode
  /** The preference to use when the browser has not stored one. */
  defaultPreference?: ThemePreference
  /** Where the preference is remembered. */
  storageKey?: string
}

/** The local storage, or `null` when the browser has none. */
function safeStorage(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage
  } catch {
    // Some browsers throw on the property access itself when storage is
    // disabled by policy.
    return null
  }
}

export function ThemeProvider({
  children,
  defaultPreference = 'dark',
  storageKey = THEME_STORAGE_KEY,
}: ThemeProviderProps) {
  const storage = useMemo(safeStorage, [])

  const [preference, setPreferenceState] = useState<ThemePreference>(() => {
    const stored = readStoredPreference(storage, storageKey)
    return stored ?? defaultPreference
  })

  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(readSystemTheme)

  // Follow the operating system while the preference is `system`.
  useEffect(() => {
    if (preference !== 'system') return
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return

    let query: MediaQueryList
    try {
      query = window.matchMedia(DARK_SCHEME_QUERY)
    } catch {
      return
    }

    const onChange = (event: MediaQueryListEvent) => {
      setSystemTheme(event.matches ? 'dark' : 'light')
    }

    setSystemTheme(query.matches ? 'dark' : 'light')
    query.addEventListener('change', onChange)
    return () => {
      query.removeEventListener('change', onChange)
    }
  }, [preference])

  const resolvedTheme = resolveTheme(preference, systemTheme)

  // Put the theme on the document so the tokens reach the portals too.
  useEffect(() => {
    if (typeof document === 'undefined') return
    document.documentElement.classList.toggle('dark', resolvedTheme === 'dark')
  }, [resolvedTheme])

  const setPreference = useCallback(
    (next: ThemePreference) => {
      setPreferenceState(next)
      writeStoredPreference(storage, storageKey, next)
    },
    [storage, storageKey],
  )

  const toggle = useCallback(() => {
    setPreferenceState((current) => {
      const resolved = resolveTheme(current, systemTheme)
      const next: ThemePreference = resolved === 'dark' ? 'light' : 'dark'
      writeStoredPreference(storage, storageKey, next)
      return next
    })
  }, [systemTheme, storage, storageKey])

  const value = useMemo<ThemeContextValue>(
    () => ({ preference, resolvedTheme, setPreference, toggle }),
    [preference, resolvedTheme, setPreference, toggle],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
