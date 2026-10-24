import { describe, expect, it } from 'vitest'

import { memoryFigures, storageFigure } from './specs'

describe('memoryFigures', () => {
  it('says both figures for a product that has them', () => {
    expect(memoryFigures({ storage_gb: '512', ram_gb: '18' })).toBe('512/18')
  })

  it('says whichever figure the product does have', () => {
    expect(memoryFigures({ storage_gb: '256', ram_gb: '' })).toBe('256')
  })

  it('says nothing for a product that has neither', () => {
    // A hair dryer has neither, and the catalogue records that by leaving
    // the columns blank. Writing "0/0" here would be a lie about the dryer,
    // and writing "512/18" would be a lie about the data.
    expect(memoryFigures({ storage_gb: '', ram_gb: '' })).toBe('')
  })
})

describe('storageFigure', () => {
  it('says the capacity with its unit', () => {
    expect(storageFigure({ storage_gb: '512', ram_gb: '18' })).toBe('512GB')
  })

  it('says nothing for a product with no storage', () => {
    expect(storageFigure({ storage_gb: '', ram_gb: '' })).toBe('')
  })
})
