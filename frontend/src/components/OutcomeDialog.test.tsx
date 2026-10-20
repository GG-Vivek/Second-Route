import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OutcomeDialog } from '@/components/OutcomeDialog'

const createOutcomeMock = vi.fn()

vi.mock('@/api/decision', () => ({
  createOutcome: (...args: unknown[]) => createOutcomeMock(...args),
}))

describe('OutcomeDialog', () => {
  beforeEach(() => {
    createOutcomeMock.mockReset()
    createOutcomeMock.mockResolvedValue({
      id: 'outcome-1',
      unit_id: 'unit-1',
      decision_id: 'decision-1',
      channel_taken: 'RESELL_OPEN_BOX',
      sale_price: 1000,
      fees_actual: 120,
      repair_cost_actual: 0,
      logistics_actual: 25,
      days_to_disposition: 7,
      final_status: 'sold',
      recorded_at: '2026-10-20T12:00:00Z',
      net: 855,
    })
  })

  it('renders nothing when closed', () => {
    const { container } = render(
      <OutcomeDialog
        unitId="unit-1"
        decisionId="decision-1"
        recommendedChannel="RESELL_OPEN_BOX"
        availableChannels={['RESELL_OPEN_BOX', 'RESELL_REFURB']}
        open={false}
        onClose={() => {}}
      />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('preselects the recommended channel', () => {
    render(
      <OutcomeDialog
        unitId="unit-1"
        decisionId="decision-1"
        recommendedChannel="RESELL_OPEN_BOX"
        availableChannels={['RESELL_OPEN_BOX', 'RESELL_REFURB']}
        open
        onClose={() => {}}
      />
    )
    expect(screen.getByLabelText(/channel used/i)).toHaveValue('RESELL_OPEN_BOX')
  })

  it('keeps submit disabled until every number is provided', async () => {
    render(
      <OutcomeDialog
        unitId="unit-1"
        decisionId="decision-1"
        recommendedChannel="RESELL_OPEN_BOX"
        availableChannels={['RESELL_OPEN_BOX', 'RESELL_REFURB']}
        open
        onClose={() => {}}
      />
    )

    const submit = screen.getByRole('button', { name: /record outcome/i })
    expect(submit).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/sale price/i), '1000')
    expect(submit).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/fees/i), '120')
    await userEvent.type(screen.getByLabelText(/repair cost/i), '0')
    await userEvent.type(screen.getByLabelText(/logistics cost/i), '25')
    await userEvent.type(screen.getByLabelText(/days to disposition/i), '7')

    expect(submit).toBeEnabled()
  })

  it('previews the realized net as the numbers are entered', async () => {
    render(
      <OutcomeDialog
        unitId="unit-1"
        decisionId="decision-1"
        recommendedChannel="RESELL_OPEN_BOX"
        availableChannels={['RESELL_OPEN_BOX', 'RESELL_REFURB']}
        open
        onClose={() => {}}
      />
    )

    await userEvent.type(screen.getByLabelText(/sale price/i), '1000')
    await userEvent.type(screen.getByLabelText(/fees/i), '120')
    await userEvent.type(screen.getByLabelText(/repair cost/i), '0')
    await userEvent.type(screen.getByLabelText(/logistics cost/i), '25')

    expect(screen.getByTestId('outcome-net-preview')).toHaveTextContent('$855.00')
  })

  it('submits the realized numbers with the decision id', async () => {
    const onSuccess = vi.fn()
    render(
      <OutcomeDialog
        unitId="unit-1"
        decisionId="decision-1"
        recommendedChannel="RESELL_OPEN_BOX"
        availableChannels={['RESELL_OPEN_BOX', 'RESELL_REFURB']}
        open
        onClose={() => {}}
        onSuccess={onSuccess}
      />
    )

    await userEvent.type(screen.getByLabelText(/sale price/i), '1000')
    await userEvent.type(screen.getByLabelText(/fees/i), '120')
    await userEvent.type(screen.getByLabelText(/repair cost/i), '0')
    await userEvent.type(screen.getByLabelText(/logistics cost/i), '25')
    await userEvent.type(screen.getByLabelText(/days to disposition/i), '7')
    await userEvent.click(screen.getByRole('button', { name: /record outcome/i }))

    await waitFor(() => {
      expect(createOutcomeMock).toHaveBeenCalledWith('unit-1', {
        channel_taken: 'RESELL_OPEN_BOX',
        sale_price: 1000,
        fees_actual: 120,
        repair_cost_actual: 0,
        logistics_actual: 25,
        days_to_disposition: 7,
        final_status: 'sold',
        decision_id: 'decision-1',
      })
    })
    expect(onSuccess).toHaveBeenCalled()
  })

  it('shows an error when the unit has no decision to link to', async () => {
    createOutcomeMock.mockRejectedValue({ response: { status: 404 } })

    render(
      <OutcomeDialog
        unitId="unit-1"
        decisionId={null}
        recommendedChannel="RESELL_OPEN_BOX"
        availableChannels={['RESELL_OPEN_BOX']}
        open
        onClose={() => {}}
      />
    )

    await userEvent.type(screen.getByLabelText(/sale price/i), '1000')
    await userEvent.type(screen.getByLabelText(/fees/i), '120')
    await userEvent.type(screen.getByLabelText(/repair cost/i), '0')
    await userEvent.type(screen.getByLabelText(/logistics cost/i), '25')
    await userEvent.type(screen.getByLabelText(/days to disposition/i), '7')
    await userEvent.click(screen.getByRole('button', { name: /record outcome/i }))

    await waitFor(() => {
      expect(screen.getByText(/no decision to link/i)).toBeInTheDocument()
    })
  })
})
