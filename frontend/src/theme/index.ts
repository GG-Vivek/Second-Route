/**
 * The theme module (F8.1).
 *
 * Re-exports the public surface so callers import from one place.
 */

export {
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
export { ThemeProvider, type ThemeProviderProps } from './ThemeProvider'
export { useTheme } from './useTheme'
