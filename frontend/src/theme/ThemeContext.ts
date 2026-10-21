/**
 * The theme context and its types.
 *
 * The context lives in its own module so that the provider file exports
 * only a component, which keeps React Fast Refresh working in development.
 * The same reason made the offline module split its hook out.
 */

import { createContext } from 'react'

/** What the user chose. `system` defers to the operating system. */
export type ThemePreference = 'light' | 'dark' | 'system'

/** What is actually on screen. `system` has already been resolved. */
export type ResolvedTheme = 'light' | 'dark'

export interface ThemeContextValue {
  /** The preference the user chose. */
  preference: ThemePreference
  /** The theme that is in effect right now. */
  resolvedTheme: ResolvedTheme
  /** Change the preference. It is remembered. */
  setPreference: (preference: ThemePreference) => void
  /** Flip between light and dark. */
  toggle: () => void
}

export const ThemeContext = createContext<ThemeContextValue | null>(null)

/** The key the preference is stored under. */
export const THEME_STORAGE_KEY = 'secondroute-theme'

/** The media query that reports the operating system's preference. */
export const DARK_SCHEME_QUERY = '(prefers-color-scheme: dark)'

/**
 * Resolve a preference into the theme that is in effect.
 *
 * `system` is the only preference that is not already a theme.
 */
export function resolveTheme(
  preference: ThemePreference,
  systemTheme: ResolvedTheme,
): ResolvedTheme {
  return preference === 'system' ? systemTheme : preference
}

/**
 * Read the stored preference.
 *
 * Returns `null` when nothing is stored or when the browser refuses to
 * answer. A browser with storage disabled is a supported browser.
 */
export function readStoredPreference(storage: Storage | null, key: string): ThemePreference | null {
  if (!storage) return null
  try {
    const stored = storage.getItem(key)
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored
    }
    return null
  } catch {
    // A storage failure must not stop the application from rendering.
    return null
  }
}

/** Write the preference down, ignoring a browser that refuses. */
export function writeStoredPreference(
  storage: Storage | null,
  key: string,
  preference: ThemePreference,
): void {
  if (!storage) return
  try {
    storage.setItem(key, preference)
  } catch {
    // The theme still changes for this session; it just is not remembered.
  }
}

/** Ask the browser which theme it would prefer. */
export function readSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return 'dark'
  }
  try {
    return window.matchMedia(DARK_SCHEME_QUERY).matches ? 'dark' : 'light'
  } catch {
    return 'dark'
  }
}
