import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DecisionCard } from '@/components/decision/DecisionCard'
import type { Decision } from '@/types/decision'

function makeCandidate(overrides: Partial<Decision['candidates'][number]> = {}) {
  return {
    channel: 'RESELL_OPEN_BOX' as const,
    eligible: true,
    exclusion_reason: null,
    mean: 1200,
    stddev: 90,
    p10: 1000,
    p50: 1200,
    p90: 1400,
    probability_best: 0.82,
    certainty_equivalent: 1110,
    grade_probabilities: { A: 0.8, B: 0.15, C: 0.04, D: 0.01 },
    price_sources: { 'RESELL_OPEN_BOX:A': 'synthetic' },
    price_as_of: { 'RESELL_OPEN_BOX:A': '2025-06-01T00:00:00' },
    breakdown: {
      sale_price: 1600,
      fees: 190,
      logistics: 28,
      handling: 18,
      repair: 15,
      holding: 2,
      total_cost: 253,
      net: 1347,
    },
    ...overrides,
  }
}

function makeDecision(overrides: Partial<Decision> = {}): Decision {
  return {
    id: 'decision-1',
    unit_id: 'unit-1',
    created_at: '2025-06-01T12:00:00Z',
    model_version: 'decision-v1',
    risk_profile: 'balanced',
    recommended_channel: 'RESELL_OPEN_BOX',
    confidence: 0.86,
    fallback_used: false,
    fallback_channel: null,
    candidates: [
      makeCandidate(),
      makeCandidate({
        channel: 'RESELL_REFURB',
        mean: 700,
        p10: 500,
        p50: 700,
        p90: 900,
        probability_best: 0.18,
        certainty_equivalent: 620,
      }),
      makeCandidate({
        channel: 'RECYCLE',
        mean: 40,
        p10: 20,
        p50: 40,
        p90: 60,
        probability_best: 0,
        certainty_equivalent: 30,
      }),
      makeCandidate({
        channel: 'DONATE',
        mean: -45,
        p10: -50,
        p50: -45,
        p90: -40,
        probability_best: 0,
        certainty_equivalent: -50,
      }),
    ],
    reasons: [
      {
        code: 'favourable_sale_price',
        label: 'Expected sale price',
        contribution: 320,
        favours_recommended: true,
        text: 'Resell as open-box wins on expected sale price: $320.00 better than refurbish and resell.',
      },
    ],
    flip_conditions: [
      {
        input_name: 'channel_fee_pct',
        input_kind: 'numeric',
        current_value: 0.12,
        threshold_value: 0.28,
        new_channel: 'RESELL_REFURB',
        direction: 'above',
        description: 'If platform fee were above 28.0% the recommendation would become refurbish and resell.',
        target_channel: 'RESELL_OPEN_BOX',
      },
    ],
    action_steps: [
      {
        order: 1,
        title: 'Wipe the device',
        detail: 'Factory-reset the device before it leaves the warehouse.',
        reference: 'NIST SP 800-88 Rev. 1',
      },
    ],
    data_freshness: {
      price_sources: {},
      price_as_of: {},
      cost_sources: {},
      cost_as_of: {},
      is_synthetic: true,
      warnings: ['Prices are synthetic. This is a prototype, not a money claim.'],
    },
    input_snapshot_hash: 'abc123',
    is_prototype: true,
    prototype_badge: 'Prototype - synthetic prices',
    ...overrides,
  }
}

describe('DecisionCard', () => {
  it('shows the prototype badge', () => {
    render(<DecisionCard decision={makeDecision()} />)
    expect(screen.getByTestId('prototype-badge')).toBeInTheDocument()
    expect(screen.getByText('Prototype - synthetic prices')).toBeInTheDocument()
  })

  it('shows the recommended channel', () => {
    render(<DecisionCard decision={makeDecision()} />)
    expect(screen.getByRole('heading', { name: 'Resell as open-box' })).toBeInTheDocument()
  })

  it('shows the confidence', () => {
    render(<DecisionCard decision={makeDecision()} />)
    expect(screen.getByText('86.0%')).toBeInTheDocument()
  })

  it('shows the net range', () => {
    render(<DecisionCard decision={makeDecision()} />)
    expect(screen.getByText(/p10 \$1,000\.00/)).toBeInTheDocument()
    expect(screen.getByText(/p50 \$1,200\.00/)).toBeInTheDocument()
    expect(screen.getByText(/p90 \$1,400\.00/)).toBeInTheDocument()
  })

  it('lists the alternative channels with deltas', () => {
    render(<DecisionCard decision={makeDecision()} />)
    expect(screen.getByTestId('candidate-RESELL_REFURB')).toBeInTheDocument()
    expect(screen.getByTestId('candidate-RECYCLE')).toBeInTheDocument()
    expect(screen.getByText('-$500.00')).toBeInTheDocument()
  })

  it('shows the reasons', () => {
    render(<DecisionCard decision={makeDecision()} />)
    expect(screen.getByTestId('reasons-list')).toBeInTheDocument()
    expect(screen.getByText(/wins on expected sale price/)).toBeInTheDocument()
  })

  it('shows the flip conditions', () => {
    render(<DecisionCard decision={makeDecision()} />)
    expect(screen.getByTestId('flip-conditions-list')).toBeInTheDocument()
    expect(screen.getByText(/the recommendation would become refurbish and resell/)).toBeInTheDocument()
  })

  it('shows the action steps', () => {
    render(<DecisionCard decision={makeDecision()} />)
    expect(screen.getByTestId('action-steps-list')).toBeInTheDocument()
    expect(screen.getByText('Wipe the device')).toBeInTheDocument()
    expect(screen.getByText(/NIST SP 800-88 Rev\. 1/)).toBeInTheDocument()
  })

  it('offers an accept button and nothing else', () => {
    render(<DecisionCard decision={makeDecision()} />)
    expect(screen.getByTestId('accept-button')).toBeInTheDocument()
    // Overrides arrive in Phase 4, so no override control is rendered yet.
    expect(screen.queryByRole('button', { name: /override/i })).not.toBeInTheDocument()
  })

  it('calls onAccept when the button is clicked', async () => {
    const onAccept = vi.fn()
    render(<DecisionCard decision={makeDecision()} onAccept={onAccept} />)
    await userEvent.click(screen.getByTestId('accept-button'))
    expect(onAccept).toHaveBeenCalledTimes(1)
  })

  it('renders a SAFE_DEFAULT decision with a human check warning', () => {
    const decision = makeDecision({
      recommended_channel: 'SAFE_DEFAULT',
      fallback_used: true,
      fallback_channel: 'RESELL_OPEN_BOX',
      confidence: 0.42,
    })
    render(<DecisionCard decision={decision} />)

    expect(screen.getByRole('heading', { name: /Safe default/ })).toBeInTheDocument()
    expect(screen.getByText('Needs a human check')).toBeInTheDocument()
    expect(screen.getByText(/Conservative floor: Resell as open-box/)).toBeInTheDocument()
  })

  it('renders a flip condition free decision without the section', () => {
    const decision = makeDecision({ flip_conditions: [] })
    render(<DecisionCard decision={decision} />)
    expect(screen.queryByTestId('flip-conditions-list')).not.toBeInTheDocument()
  })
})
