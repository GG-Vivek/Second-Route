/**
 * What a hue means (ADR-008).
 *
 * The tokens have carried seven accents and five callout roles since F8.1,
 * but they were decoration: every chart, every badge and every bar was drawn
 * in the one brand hue, so a reader could not tell two series apart by
 * looking. This module is the single place that says what each hue is for,
 * so that the same colour says the same thing everywhere it is drawn, in
 * both applications and in both themes.
 *
 * The hues are not palette choices; they are statements about the data. A
 * chart that colours a modelled number like a measured one is lying with a
 * colour, and the class names here are the reason that is hard to do by
 * accident.
 */

/** The seven accents, named as the tokens name them. */
export type Hue = 'lime' | 'teal' | 'cyan' | 'purple' | 'orange' | 'yellow' | 'red'

/**
 * The meanings, and the hue that carries each one.
 *
 * Every entry gets a class of its own below: Tailwind builds the stylesheet
 * by scanning the source, so the full class name has to appear here as it is
 * written, not be assembled at runtime.
 */
export const MEANING = {
  /** The brand, the recommended thing, the value that was actually recovered. */
  recovered: 'lime',
  /** A baseline, an observation, a measurement: something that happened. */
  measured: 'teal',
  /** A second measured series, when two have to be told apart. */
  alsoMeasured: 'cyan',
  /** A caution: a cost, an ageing thing, a reason for attention. */
  caution: 'orange',
  /** An estimate, a model artefact, anything nobody observed. */
  estimated: 'purple',
  /** Synthetic data, which must never be read as a measurement. */
  synthetic: 'yellow',
  /** Destructive, or missing altogether. */
  missing: 'red',
} as const

/** The meanings, for a signature that has to name them. */
export type Meaning = keyof typeof MEANING

const TEXT = {
  recovered: 'text-lime',
  measured: 'text-teal',
  alsoMeasured: 'text-cyan',
  caution: 'text-orange',
  estimated: 'text-purple',
  synthetic: 'text-yellow',
  missing: 'text-red',
} as const

const FILL = {
  recovered: 'bg-lime',
  measured: 'bg-teal',
  alsoMeasured: 'bg-cyan',
  caution: 'bg-orange',
  estimated: 'bg-purple',
  synthetic: 'bg-yellow',
  missing: 'bg-red',
} as const

/** The class that writes a meaning as text. */
export function textFor<M extends Meaning>(meaning: M): (typeof TEXT)[M] {
  return TEXT[meaning]
}

/** The class that fills a shape with a meaning. */
export function fillFor<M extends Meaning>(meaning: M): (typeof FILL)[M] {
  return FILL[meaning]
}
