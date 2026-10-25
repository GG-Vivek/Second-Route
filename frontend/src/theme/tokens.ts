import type { Rgb } from './contrast'

/**
 * The design tokens, read from the stylesheet they are written in.
 *
 * The contrast suite and the palette rules both measure `index.css` rather
 * than a copy of it, so a value that is edited here is measured again the next
 * time the suite runs, and a token that is renamed cannot leave a stale number
 * behind in a test.
 *
 * Only colour tokens are read: a token that is a length or a duration is not
 * something a reader has to be able to see.
 */

/** The colour tokens declared under one selector. */
export type TokenSet = Record<string, Rgb>

/** A stylesheet with a `:root` block and a `.dark` block. */
const COLOUR_DECLARATION = /--([\w-]+):\s*(\d+)\s+(\d+)\s+(\d+)(?:\s*\/\s*[\d.]+)?\s*;/g

/** The stylesheet with the comments removed, so prose cannot be parsed. */
function stripComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, '')
}

/**
 * The colour tokens declared directly inside one selector's block.
 *
 * Braces are counted rather than assumed: the block is a slice of a real
 * stylesheet, and a rule nested inside it ends where it ends and not where
 * the next line begins.
 */
export function readColourBlock(css: string, selector: string): TokenSet {
  const source = stripComments(css)
  const pattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{`)
  const match = pattern.exec(source)
  if (!match) {
    throw new Error(
      `the stylesheet declares no ${selector} block (it begins: ${source.slice(0, 120)})`
    )
  }
  const start = match.index

  const open = source.indexOf('{', start)
  let depth = 0
  let end = -1
  for (let index = open; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') {
      depth -= 1
      if (depth === 0) {
        end = index
        break
      }
    }
  }
  if (end === -1) {
    throw new Error(`the ${selector} block is never closed`)
  }

  const tokens: TokenSet = {}
  const block = source.slice(open, end)
  for (const match of block.matchAll(COLOUR_DECLARATION)) {
    tokens[match[1]] = { r: Number(match[2]), g: Number(match[3]), b: Number(match[4]) }
  }
  return tokens
}

/**
 * Both themes, as the browser computes them.
 *
 * The dark block is layered over the light one exactly as the cascade layers
 * them, so a token the dark block leaves out — the callout containers, which
 * read the same in both themes — keeps the value the light block gave it.
 *
 * The stylesheet is passed in rather than opened here: a module that reads a
 * file is a module that cannot be tested from anywhere but the one directory
 * it happens to live in.
 */
export function stylesheetTokens(css: string): { light: TokenSet; dark: TokenSet } {
  const light = readColourBlock(css, ':root')
  const dark = readColourBlock(css, '.dark')
  return { light, dark: { ...light, ...dark } }
}
