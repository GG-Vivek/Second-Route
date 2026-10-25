import { describe, it, expect } from 'vitest'
import { readSource } from '@/test/source'
import { contrastRatio, parseRgb, type Rgb } from '@/theme/contrast'
import { stylesheetTokens, type TokenSet } from '@/theme/tokens'

/**
 * The colour pairs the interface actually draws.
 *
 * Every one of these is a background and a foreground that appear next to
 * each other on the page. The thresholds are the Web Content Accessibility
 * Guidelines: 4.5 to one for body text, and 3 to one for large text and
 * for the boundary of a control.
 *
 * A pair that fails here is a pair somebody cannot read. The *pairing* is
 * written here because which foreground sits on which background is a design
 * decision; the numbers come out of `index.css`, so that a colour which
 * changes is measured again.
 */
interface Pair {
  /** What the pair is used for. */
  name: string
  /** The foreground, as the token that draws it. */
  foreground: string
  /** The background, as the token that paints it. */
  background: string
  /** The minimum ratio. Large text and control boundaries need less. */
  minimum?: number
}

const BODY = 4.5
const LARGE = 3
/** A divider is decoration. It has to be visible, not to be read. */
const DECORATION = 1.5

/**
 * The pairs, in the order the two themes declare them. The token names are
 * the same in both: only the values differ, which is the point of a token.
 */
const PAIRS: Pair[] = [
  { name: 'the page', foreground: 'foreground', background: 'background' },
  { name: 'a card', foreground: 'foreground', background: 'card' },
  { name: 'muted text on a card', foreground: 'muted-foreground', background: 'card' },

  { name: 'the primary button', foreground: 'primary-foreground', background: 'primary' },
  { name: 'the lime badge', foreground: 'on-lime', background: 'lime' },
  { name: 'the teal badge', foreground: 'on-teal', background: 'teal' },
  { name: 'the cyan badge', foreground: 'on-cyan', background: 'cyan' },
  { name: 'the purple badge', foreground: 'on-purple', background: 'purple' },
  { name: 'the orange badge', foreground: 'on-orange', background: 'orange' },
  { name: 'the yellow badge', foreground: 'on-yellow', background: 'yellow' },
  { name: 'the red badge', foreground: 'on-red', background: 'red' },

  { name: 'the note callout', foreground: 'on-note-container', background: 'note-container' },
  { name: 'the tip callout', foreground: 'on-tip-container', background: 'tip-container' },
  {
    name: 'the important callout',
    foreground: 'on-important-container',
    background: 'important-container',
  },
  {
    name: 'the warning callout',
    foreground: 'on-warning-container',
    background: 'warning-container',
  },
  {
    name: 'the caution callout',
    foreground: 'on-caution-container',
    background: 'caution-container',
  },

  { name: 'the code island', foreground: 'code-foreground', background: 'code-background' },

  { name: 'destructive text on a card', foreground: 'destructive', background: 'card' },
  { name: 'the lime accent on a card', foreground: 'lime', background: 'card' },
  { name: 'the teal accent on a card', foreground: 'teal', background: 'card' },
  { name: 'the secondary chip', foreground: 'secondary-foreground', background: 'secondary' },

  { name: 'the outline on the page', foreground: 'outline', background: 'background', minimum: LARGE },
  {
    name: 'the boundary of a control',
    foreground: 'input',
    background: 'background',
    minimum: LARGE,
  },
  { name: 'a divider', foreground: 'border', background: 'background', minimum: DECORATION },
]

const themes = stylesheetTokens(readSource('src/index.css', 'frontend/src/index.css'))

/** A colour as the token holds it: three channels, space separated. */
function rgb({ r, g, b }: Rgb): string {
  return `${r} ${g} ${b}`
}

/** The colour a pair draws, or a failure naming what is missing. */
function colour(theme: TokenSet, token: string, pair: Pair): Rgb {
  const value = theme[token]
  if (!value) {
    throw new Error(`"${pair.name}" draws --${token}, which the stylesheet does not declare`)
  }
  return value
}

describe.each([
  ['the dark theme', themes.dark],
  ['the light theme', themes.light],
])('the contrast in %s', (_name, theme) => {
  for (const pair of PAIRS) {
    it(`${pair.name} can be read`, () => {
      const ratio = contrastRatio(
        parseRgb(rgb(colour(theme, pair.foreground, pair))),
        parseRgb(rgb(colour(theme, pair.background, pair)))
      )
      expect(
        ratio,
        `${pair.name}: ${ratio.toFixed(2)} to one, which needs ${pair.minimum ?? BODY}`
      ).toBeGreaterThanOrEqual(pair.minimum ?? BODY)
    })
  }
})
