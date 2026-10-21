import { describe, it, expect } from 'vitest'
import { contrastRatio, parseRgb } from '@/theme/contrast'

/**
 * The colour pairs the interface actually draws.
 *
 * Every one of these is a background and a foreground that appear next to
 * each other on the page. The thresholds are the Web Content Accessibility
 * Guidelines: 4.5 to one for body text, and 3 to one for large text and
 * for the boundary of a control.
 *
 * A pair that fails here is a pair somebody cannot read.
 */
interface Pair {
  /** What the pair is used for. */
  name: string
  /** The foreground, as the token holds it. */
  foreground: [number, number, number]
  /** The background, as the token holds it. */
  background: [number, number, number]
  /** The minimum ratio. Large text and control boundaries need less. */
  minimum?: number
}

const BODY = 4.5
const LARGE = 3
/** A divider is decoration. It has to be visible, not to be read. */
const DECORATION = 1.5

const DARK: Pair[] = [
  {
    name: 'the page',
    foreground: [230, 226, 221],
    background: [20, 19, 17],
  },
  {
    name: 'a card',
    foreground: [230, 226, 221],
    background: [29, 27, 25],
  },
  {
    name: 'muted text on a card',
    foreground: [198, 200, 184],
    background: [29, 27, 25],
  },
  {
    name: 'the primary button',
    foreground: [40, 53, 0],
    background: [200, 242, 64],
  },
  {
    name: 'the lime badge',
    foreground: [40, 53, 0],
    background: [200, 242, 64],
  },
  {
    name: 'the teal badge',
    foreground: [0, 56, 36],
    background: [214, 255, 228],
  },
  {
    name: 'the cyan badge',
    foreground: [0, 54, 60],
    background: [170, 240, 255],
  },
  {
    name: 'the purple badge',
    foreground: [43, 10, 48],
    background: [244, 174, 255],
  },
  {
    name: 'the orange badge',
    foreground: [41, 26, 0],
    background: [255, 227, 183],
  },
  {
    name: 'the yellow badge',
    foreground: [65, 73, 0],
    background: [255, 255, 255],
  },
  {
    name: 'the red badge',
    foreground: [105, 0, 5],
    background: [255, 177, 192],
  },
  {
    name: 'the note callout',
    foreground: [255, 253, 255],
    background: [0, 121, 199],
  },
  {
    name: 'the tip callout',
    foreground: [251, 255, 240],
    background: [73, 131, 29],
  },
  {
    name: 'the important callout',
    foreground: [255, 253, 255],
    background: [104, 97, 240],
  },
  {
    name: 'the warning callout',
    foreground: [69, 56, 0],
    background: [191, 161, 35],
  },
  {
    name: 'the caution callout',
    foreground: [255, 253, 255],
    background: [206, 72, 0],
  },
  {
    name: 'the code island',
    foreground: [251, 252, 246],
    background: [25, 27, 22],
  },
  {
    name: 'destructive text on a card',
    foreground: [255, 77, 130],
    background: [29, 27, 25],
  },
  {
    name: 'the lime accent on a card',
    foreground: [200, 242, 64],
    background: [29, 27, 25],
  },
  {
    name: 'the outline on the page',
    foreground: [144, 146, 132],
    background: [20, 19, 17],
    minimum: LARGE,
  },
  {
    name: 'the boundary of a control',
    foreground: [144, 146, 132],
    background: [20, 19, 17],
    minimum: LARGE,
  },
  {
    name: 'a divider',
    foreground: [70, 72, 60],
    background: [20, 19, 17],
    minimum: DECORATION,
  },
]

const LIGHT: Pair[] = [
  {
    name: 'the page',
    foreground: [29, 27, 25],
    background: [254, 248, 244],
  },
  {
    name: 'a card',
    foreground: [29, 27, 25],
    background: [248, 243, 238],
  },
  {
    name: 'muted text on a card',
    foreground: [70, 72, 60],
    background: [248, 243, 238],
  },
  {
    name: 'the primary button',
    foreground: [255, 255, 255],
    background: [80, 102, 0],
  },
  {
    name: 'the lime badge',
    foreground: [255, 255, 255],
    background: [80, 102, 0],
  },
  {
    name: 'the teal badge',
    foreground: [255, 255, 255],
    background: [0, 108, 69],
  },
  {
    name: 'the cyan badge',
    foreground: [255, 255, 255],
    background: [0, 104, 118],
  },
  {
    name: 'the purple badge',
    foreground: [255, 255, 255],
    background: [155, 0, 190],
  },
  {
    name: 'the orange badge',
    foreground: [255, 255, 255],
    background: [124, 88, 0],
  },
  {
    name: 'the yellow badge',
    foreground: [255, 255, 255],
    background: [91, 100, 0],
  },
  {
    name: 'the red badge',
    foreground: [255, 255, 255],
    background: [183, 0, 78],
  },
  {
    name: 'the note callout',
    foreground: [255, 253, 255],
    background: [0, 121, 199],
  },
  {
    name: 'the tip callout',
    foreground: [251, 255, 240],
    background: [73, 131, 29],
  },
  {
    name: 'the important callout',
    foreground: [255, 253, 255],
    background: [104, 97, 240],
  },
  {
    name: 'the warning callout',
    foreground: [69, 56, 0],
    background: [191, 161, 35],
  },
  {
    name: 'the caution callout',
    foreground: [255, 253, 255],
    background: [206, 72, 0],
  },
  {
    name: 'the code island',
    foreground: [251, 252, 246],
    background: [25, 27, 22],
  },
  {
    name: 'destructive text on a card',
    foreground: [183, 0, 78],
    background: [248, 243, 238],
  },
  {
    name: 'the lime accent on a card',
    foreground: [80, 102, 0],
    background: [248, 243, 238],
  },
  {
    name: 'the outline on the page',
    foreground: [118, 120, 107],
    background: [254, 248, 244],
    minimum: LARGE,
  },
  {
    name: 'the boundary of a control',
    foreground: [118, 120, 107],
    background: [254, 248, 244],
    minimum: LARGE,
  },
  {
    name: 'a divider',
    foreground: [198, 200, 184],
    background: [254, 248, 244],
    minimum: DECORATION,
  },
]

describe.each([
  ['the dark theme', DARK],
  ['the light theme', LIGHT],
])('the contrast in %s', (_name, pairs) => {
  for (const pair of pairs) {
    it(`${pair.name} can be read`, () => {
      const ratio = contrastRatio(
        parseRgb(pair.foreground.join(' ')),
        parseRgb(pair.background.join(' '))
      )
      expect(
        ratio,
        `${pair.name}: ${ratio.toFixed(2)} to one, which needs ${pair.minimum ?? BODY}`
      ).toBeGreaterThanOrEqual(pair.minimum ?? BODY)
    })
  }
})
