/**
 * Read the theme.
 *
 * Kept in its own module so the provider file only exports a component,
 * which keeps React Fast Refresh working in development.
 */

import { useContext } from 'react'
import { ThemeContext, type ThemeContextValue } from './ThemeContext'

/**
 * Read the current theme and the way to change it.
 *
 * Throws when used outside a `ThemeProvider`, because a component that
 * changes the theme has to be able to rely on there being one.
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (context === null) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
