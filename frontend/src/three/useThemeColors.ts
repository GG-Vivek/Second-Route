import { useEffect, useMemo, useState } from 'react'
import { useTheme } from '@/theme'

/** Read a colour token out of the document. */
function readColor(token: string): string {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return '#000000'
  }
  const raw = getComputedStyle(document.documentElement).getPropertyValue(token).trim()
  if (!raw) return '#000000'

  // The tokens are stored as red, green and blue channels.
  const parts = raw.split(/[\s,]+/).map(Number)
  if (parts.length >= 3 && parts.every((part) => !Number.isNaN(part))) {
    return `rgb(${parts[0]}, ${parts[1]}, ${parts[2]})`
  }
  return raw
}

/**
 * Read a colour token out of the document.
 *
 * The three-dimensional scene draws with real colours, not with CSS
 * classes, so it has to be told what the tokens currently say. Reading
 * them out of the document keeps the scene in step with the theme: the
 * lime ridge is lime in the light theme and lime in the dark one, without
 * the values being written down twice.
 *
 * The token is read again whenever the theme changes, because the two
 * themes define different values for the same name.
 */
export function useThemeColor(token: string): string {
  const { resolvedTheme } = useTheme()
  const [color, setColor] = useState(() => readColor(token))

  useEffect(() => {
    setColor(readColor(token))
  }, [token, resolvedTheme])

  return color
}

/** The colours the landscape is drawn with. */
export interface LandscapeColors {
  /** The recommended channel. */
  recommended: string
  /** The other channels. */
  other: string
  /** The grid on the floor. */
  grid: string
  /** The text of the labels. */
  label: string
}

export function useLandscapeColors(): LandscapeColors {
  const recommended = useThemeColor('--primary')
  const other = useThemeColor('--muted-foreground')
  const grid = useThemeColor('--border')
  const label = useThemeColor('--foreground')

  return useMemo(
    () => ({ recommended, other, grid, label }),
    [recommended, other, grid, label]
  )
}
