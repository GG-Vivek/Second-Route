import { describe, it, expect } from 'vitest'
import indexHtml from '../../index.html?raw'
import providerSource from './ThemeProvider.tsx?raw'

/**
 * The application has two defaults, and they have to agree.
 *
 * One is the inline script in `index.html`, which runs before the bundle and
 * decides what the page looks like on the very first paint. The other is the
 * `defaultPreference` of `ThemeProvider`, which decides what the application
 * believes when the reader has expressed no preference. If the two disagree,
 * the page flashes one theme and settles on the other, which is exactly what
 * both of them exist to prevent.
 */

/** The theme named as the fallback when nothing has been stored. */
function declaredFallback(source: string, where: string): string {
  const fromScript = source.match(/\?\s*stored\s*:\s*'(light|dark)'/)
  const fromProvider = source.match(/defaultPreference\s*=\s*'(light|dark)'/)
  const found = fromScript?.[1] ?? fromProvider?.[1]
  if (!found) throw new Error(`no default theme found in ${where}`)
  return found
}

describe('the theme a first run opens with', () => {
  it('is light in the script that paints before the bundle', () => {
    expect(declaredFallback(indexHtml, 'index.html')).toBe('light')
  })

  it('is light in the provider', () => {
    expect(declaredFallback(providerSource, 'ThemeProvider.tsx')).toBe('light')
  })

  it('is the same in both, so the first paint cannot flash', () => {
    expect(declaredFallback(indexHtml, 'index.html')).toBe(
      declaredFallback(providerSource, 'ThemeProvider.tsx')
    )
  })

  it('does not ask for a dark surface in the browser chrome either', () => {
    // The colour around the page is drawn before any CSS has been parsed, so
    // it belongs with the default rather than with the tokens.
    const themeColor = indexHtml.match(/<meta name="theme-color" content="(#[0-9a-fA-F]{6})"/)
    expect(themeColor?.[1]?.toLowerCase()).not.toBe('#141311')
  })
})
