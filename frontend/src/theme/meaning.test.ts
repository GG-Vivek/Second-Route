import { describe, it, expect } from 'vitest'
import source from './meaning.ts?raw'
import { MEANING, fillFor, seriesHue, textFor, type Meaning } from './meaning'

/**
 * What a hue means (ADR-008).
 *
 * The rule itself is the assertion: lime is the brand and the thing that was
 * actually recovered, teal is what was measured, purple is what was modelled,
 * and so on. If somebody adds a meaning here without deciding which hue it
 * is, or reuses a hue for two things, this test says so in a sentence that
 * can be argued with.
 *
 * The second test guards something less obvious. Tailwind builds the
 * stylesheet by scanning the source for class names, so a class that is
 * assembled at runtime — `text-${hue}` — is a class that never gets built,
 * and the shape it was meant to colour comes out uncoloured. The class has to
 * appear as a literal in this module.
 */
describe('what the hues mean', () => {
  it('is the rule ADR-008 writes down', () => {
    expect(MEANING).toEqual({
      recovered: 'lime',
      measured: 'teal',
      alsoMeasured: 'cyan',
      caution: 'orange',
      estimated: 'purple',
      synthetic: 'yellow',
      missing: 'red',
    })
  })

  it('names one hue per meaning, and says so in a class the stylesheet can see', () => {
    const meanings = Object.keys(MEANING) as Meaning[]

    for (const meaning of meanings) {
      const hue = MEANING[meaning]
      expect(textFor(meaning), `${meaning} as text`).toBe(`text-${hue}`)
      expect(fillFor(meaning), `${meaning} as a fill`).toBe(`bg-${hue}`)

      expect(source, `${meaning} is not a literal in meaning.ts`).toContain(`'text-${hue}'`)
      expect(source, `${meaning} is not a literal in meaning.ts`).toContain(`'bg-${hue}'`)
    }
  })

  it('does not give two meanings the same hue', () => {
    const hues = Object.values(MEANING)
    expect(new Set(hues).size).toBe(hues.length)
  })
})

/**
 * The hue of a series (F11.8).
 *
 * Several channels are drawn on one landscape and a reader has to be able
 * to follow one of them from the curve to the label to the readout. The
 * hues come from the same table as everything else, in the order the
 * meanings were decided: the recommendation is the thing that was chosen
 * and carries the brand hue, and the alternatives walk the two measured
 * hues so that two of them are never drawn in the same colour.
 *
 * This is not the categorical ramp of thirteen hues that a chart library
 * would hand out. An alternative channel is a measurement the engine made,
 * and drawing it in the caution or the synthetic hue would say something
 * false about it in order to make it distinguishable.
 */
describe('the hue of a series', () => {
  it('gives the recommendation the brand hue, wherever it sits', () => {
    expect(seriesHue(0, true)).toBe(MEANING.recovered)
    expect(seriesHue(3, true)).toBe(MEANING.recovered)
  })

  it('alternates the two measured hues along the alternatives', () => {
    expect(seriesHue(1, false)).toBe(MEANING.measured)
    expect(seriesHue(2, false)).toBe(MEANING.alsoMeasured)
    expect(seriesHue(3, false)).toBe(MEANING.measured)
    expect(seriesHue(4, false)).toBe(MEANING.alsoMeasured)
  })

  it('never paints an alternative in the brand hue', () => {
    for (let index = 0; index < 8; index++) {
      expect(seriesHue(index, false)).not.toBe(MEANING.recovered)
    }
  })

  it('only ever answers with a hue the tokens define', () => {
    const hues = Object.values(MEANING) as string[]
    for (let index = 0; index < 8; index++) {
      for (const recommended of [true, false]) {
        expect(hues).toContain(seriesHue(index, recommended))
      }
    }
  })
})
