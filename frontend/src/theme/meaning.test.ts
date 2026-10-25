import { describe, it, expect } from 'vitest'
import source from './meaning.ts?raw'
import { MEANING, fillFor, textFor, type Meaning } from './meaning'

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
