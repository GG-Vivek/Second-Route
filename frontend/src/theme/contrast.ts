/**
 * The contrast of the colour pairs.
 *
 * The thresholds are the Web Content Accessibility Guidelines: 4.5 to one
 * for body text, 3 to one for large text and for the boundary of a control.
 */

export interface Rgb {
  r: number
  g: number
  b: number
}

export function parseRgb(value: string): Rgb {
  const parts = value.split(/[\s,]+/).map(Number)
  return { r: parts[0] ?? 0, g: parts[1] ?? 0, b: parts[2] ?? 0 }
}

function channel(value: number): number {
  const normalised = value / 255
  return normalised <= 0.03928
    ? normalised / 12.92
    : Math.pow((normalised + 0.055) / 1.055, 2.4)
}

export function relativeLuminance({ r, g, b }: Rgb): number {
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

/** The contrast between two colours, from 1 to 21. */
export function contrastRatio(foreground: Rgb, background: Rgb): number {
  const lighter = Math.max(
    relativeLuminance(foreground),
    relativeLuminance(background)
  )
  const darker = Math.min(relativeLuminance(foreground), relativeLuminance(background))
  return (lighter + 0.05) / (darker + 0.05)
}
