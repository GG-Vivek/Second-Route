import { describe, it, expect } from 'vitest'
import { readSource } from '@/test/source'
import { readColourBlock, stylesheetTokens } from './tokens'

/**
 * The tokens are measured where they are written.
 *
 * The contrast suite used to carry a copy of every colour in the theme, so a
 * value could be changed in `index.css` and the suite would keep passing
 * against numbers that no longer appear anywhere on the page. Reading the
 * stylesheet closes that hole: a colour that changes is measured again, and a
 * colour that is missing cannot be tested by accident.
 */

const css = readSource('src/index.css', 'frontend/src/index.css')
const themes = stylesheetTokens(css)
const darkBlock = readColourBlock(css, '.dark')
const lightBlock = readColourBlock(css, ':root')

/**
 * The surfaces a reader experiences as the colour of the thing they are
 * looking at. Every one of them has to be of a hue: a page whose background is
 * a warm grey near zero is a screen switched off, not a designed surface.
 */
const SURFACES = [
  'background',
  'card',
  'popover',
  'muted',
  'accent',
  'surface-2',
  'surface-3',
  'surface-4',
]

/**
 * How far the farthest channel has to be from the nearest one, out of 255,
 * before a colour counts as having a hue at all.
 */
const HUE = 6

describe('the colours the stylesheet declares', () => {
  it('declares both themes', () => {
    expect(Object.keys(themes.light).length).toBeGreaterThan(40)
    expect(themes.light.background).toBeDefined()
    expect(themes.dark.background).toBeDefined()
  })

  it('declares in the dark theme only what the light theme declares too', () => {
    const orphaned = Object.keys(darkBlock).filter((name) => !(name in lightBlock))
    expect(orphaned).toEqual([])
  })

  it('takes the tokens the dark block does not mention from the light one', () => {
    // The callout containers are deliberately the same in both themes, so the
    // dark block leaves them out and the cascade supplies them. If that ever
    // stops being true, the dark theme would inherit something unexpected.
    expect(themes.dark['note-container']).toEqual(lightBlock['note-container'])
    expect(darkBlock['note-container']).toBeUndefined()
  })

  it.each(SURFACES)('draws %s in both themes with a hue in it', (name) => {
    for (const [theme, tokens] of Object.entries(themes)) {
      const colour = tokens[name]
      if (!colour) throw new Error(`the ${theme} theme declares no --${name}`)

      const spread = Math.max(colour.r, colour.g, colour.b) - Math.min(colour.r, colour.g, colour.b)
      expect(
        spread,
        `the ${theme} --${name} has no hue in it: ${colour.r} ${colour.g} ${colour.b}`
      ).toBeGreaterThanOrEqual(HUE)
    }
  })

  it.each(SURFACES)('draws %s in both themes as something other than black', (name) => {
    for (const [theme, tokens] of Object.entries(themes)) {
      const colour = tokens[name]
      if (!colour) throw new Error(`the ${theme} theme declares no --${name}`)

      expect(colour.r + colour.g + colour.b, `the ${theme} --${name} is black`).toBeGreaterThan(0)
    }
  })
})
