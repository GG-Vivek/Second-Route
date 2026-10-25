import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SourceBadge } from './HealthPage'
import { fillFor } from '@/theme/meaning'

/**
 * What a source's condition is drawn in (ADR-008).
 *
 * A stale source is a caution and a missing one is a failure. Until now both
 * of them shared a hue with synthetic data — yellow — which is a hue the
 * palette reserves for numbers that were generated rather than collected. A
 * reader glancing at a list of sources could not tell "this has not been
 * checked in a while" from "this was never real".
 */
describe('the colour of a source condition', () => {
  it('leaves a fresh source in the brand hue, which is the state the system wants', () => {
    render(<SourceBadge status="fresh" />)

    expect(screen.getByText('Fresh')).toHaveClass(fillFor('recovered'))
  })

  it('marks a stale source as a caution rather than as synthetic data', () => {
    render(<SourceBadge status="stale" />)

    expect(screen.getByText('Stale')).toHaveClass(fillFor('caution'))
  })

  it('marks a missing source as missing', () => {
    render(<SourceBadge status="missing" />)

    expect(screen.getByText('Missing')).toHaveClass(fillFor('missing'))
  })
})
