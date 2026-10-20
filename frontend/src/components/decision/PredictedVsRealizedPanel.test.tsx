import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  PredictedVsRealizedPanel,
  PredictedVsRealizedRow,
} from '@/components/decision/PredictedVsRealizedPanel'
import type { PredictedVsRealized } from '@/types/decision'

function makeComparison(
  overrides: Partial<PredictedVsRealized> = {}
): PredictedVsRealized {
  return {
    unit_id: 'unit-1',
    decision_id: 'decision-1',
    outcome_id: 'outcome-1',
    channel: 'RESELL_OPEN_BOX',
    recommended_channel: 'RESELL_OPEN_BOX',
    used_recommended: true,
    predicted: {
      channel: 'RESELL_OPEN_BOX',
      p10: 800,
      p50: 900,
      p90: 1000,
      mean: 900,
    },
    realized_net: 950,
    residual: 50,
    absolute_residual: 50,
    in_range: true,
    within_p10_p90: true,
    below_p10: false,
    above_p90: false,
    recorded_at: '2026-10-20T12:00:00Z',
    ...overrides,
  }
}

describe('PredictedVsRealizedRow', () => {
  it('shows the predicted range and the realized net', () => {
    render(<PredictedVsRealizedRow comparison={makeComparison()} />)

    expect(screen.getByText('$800.00 – $1,000.00')).toBeInTheDocument()
    expect(screen.getByText('p50 $900.00')).toBeInTheDocument()
    expect(screen.getByText('$950.00')).toBeInTheDocument()
  })

  it('flags a realized value inside the predicted range', () => {
    render(<PredictedVsRealizedRow comparison={makeComparison()} />)
    expect(screen.getByTestId('in-range-badge')).toHaveTextContent('Inside predicted range')
  })

  it('flags a realized value below p10', () => {
    render(
      <PredictedVsRealizedRow
        comparison={makeComparison({
          in_range: false,
          within_p10_p90: false,
          below_p10: true,
          realized_net: 500,
          residual: -400,
          absolute_residual: 400,
        })}
      />
    )
    expect(screen.getByTestId('in-range-badge')).toHaveTextContent('Below p10')
  })

  it('flags a realized value above p90', () => {
    render(
      <PredictedVsRealizedRow
        comparison={makeComparison({
          in_range: false,
          within_p10_p90: false,
          above_p90: true,
          realized_net: 1200,
          residual: 300,
          absolute_residual: 300,
        })}
      />
    )
    expect(screen.getByTestId('in-range-badge')).toHaveTextContent('Above p90')
  })

  it('marks an overridden channel', () => {
    render(
      <PredictedVsRealizedRow
        comparison={makeComparison({
          channel: 'RECYCLE',
          recommended_channel: 'RESELL_OPEN_BOX',
          used_recommended: false,
        })}
      />
    )
    expect(screen.getByText(/overrode/i)).toBeInTheDocument()
  })

  it('shows a positive residual as a gain', () => {
    render(<PredictedVsRealizedRow comparison={makeComparison()} />)
    expect(screen.getByTestId('residual')).toHaveTextContent('$50.00')
  })
})

describe('PredictedVsRealizedPanel', () => {
  it('shows an empty state when there is nothing to compare', () => {
    render(<PredictedVsRealizedPanel comparisons={[]} />)
    expect(screen.getByTestId('no-comparisons')).toBeInTheDocument()
  })

  it('shows the summary stats', () => {
    render(
      <PredictedVsRealizedPanel
        comparisons={[makeComparison()]}
        summary={{
          total: 1,
          in_range_count: 1,
          in_range_rate: 1,
          below_p10_count: 0,
          above_p90_count: 0,
          used_recommended_count: 1,
          mean_residual: 50,
          mean_absolute_residual: 50,
        }}
      />
    )

    expect(screen.getByTestId('in-range-rate')).toHaveTextContent('100%')
    // Mean residual and mean absolute residual are both $50.00.
    expect(screen.getAllByText('$50.00').length).toBeGreaterThanOrEqual(2)
  })

  it('derives the summary when none is provided', () => {
    render(
      <PredictedVsRealizedPanel
        comparisons={[
          makeComparison(),
          makeComparison({
            outcome_id: 'outcome-2',
            in_range: false,
            within_p10_p90: false,
            below_p10: true,
            realized_net: 500,
            residual: -400,
            absolute_residual: 400,
          }),
        ]}
      />
    )

    expect(screen.getByTestId('in-range-rate')).toHaveTextContent('50%')
  })
})
