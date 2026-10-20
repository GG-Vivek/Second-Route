import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ExplanationPanel } from '@/components/decision/ExplanationPanel'
import type { Explanation } from '@/types/decision'

const mockExplain = vi.fn()

vi.mock('@/api/decision', () => ({
  explainDecision: (...args: unknown[]) => mockExplain(...args),
}))

function makeExplanation(overrides: Partial<Explanation> = {}): Explanation {
  return {
    id: 'explanation-1',
    decision_id: 'decision-1',
    text: 'The engine picked RESELL_OPEN_BOX at a net of 900.',
    source: 'model',
    reason: 'validated',
    model: 'qwen2.5:14b',
    unseen_numbers: [],
    created_at: '2026-10-20T12:00:00Z',
    ...overrides,
  }
}

describe('ExplanationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('offers to explain the decision', () => {
    render(<ExplanationPanel decisionId="decision-1" />)

    expect(screen.getByTestId('explain-button')).toBeInTheDocument()
    expect(screen.queryByTestId('explanation-text')).not.toBeInTheDocument()
  })

  it('shows the explanation once it is fetched', async () => {
    mockExplain.mockResolvedValue(makeExplanation())
    const user = userEvent.setup()

    render(<ExplanationPanel decisionId="decision-1" />)
    await user.click(screen.getByTestId('explain-button'))

    await waitFor(() => {
      expect(screen.getByTestId('explanation-text')).toHaveTextContent(
        'The engine picked RESELL_OPEN_BOX at a net of 900.'
      )
    })
    expect(mockExplain).toHaveBeenCalledWith('decision-1')
  })

  it('says that the model wrote it', async () => {
    mockExplain.mockResolvedValue(makeExplanation())
    const user = userEvent.setup()

    render(<ExplanationPanel decisionId="decision-1" />)
    await user.click(screen.getByTestId('explain-button'))

    await waitFor(() => {
      expect(screen.getByTestId('explanation-source')).toHaveTextContent(
        'Written by the model'
      )
    })
    expect(screen.getByTestId('explanation-reason')).toHaveTextContent(
      'Every number in it came from the decision'
    )
  })

  it('says that the template was used instead', async () => {
    mockExplain.mockResolvedValue(
      makeExplanation({
        source: 'template',
        reason: 'unseen-number',
        unseen_numbers: ['2000'],
        model: null,
      })
    )
    const user = userEvent.setup()

    render(<ExplanationPanel decisionId="decision-1" />)
    await user.click(screen.getByTestId('explain-button'))

    await waitFor(() => {
      expect(screen.getByTestId('explanation-source')).toHaveTextContent(
        'The standard template'
      )
    })
    expect(screen.getByTestId('explanation-reason')).toHaveTextContent(
      'The model mentioned a number the decision does not have'
    )
  })

  it('shows an explanation it was given', () => {
    render(<ExplanationPanel decisionId="decision-1" explanation={makeExplanation()} />)

    expect(screen.getByTestId('explanation-text')).toBeInTheDocument()
    expect(screen.queryByTestId('explain-button')).not.toBeInTheDocument()
  })

  it('reports a failure', async () => {
    mockExplain.mockRejectedValue(new Error('no model'))
    const user = userEvent.setup()

    render(<ExplanationPanel decisionId="decision-1" />)
    await user.click(screen.getByTestId('explain-button'))

    await waitFor(() => {
      expect(screen.getByTestId('explanation-error')).toBeInTheDocument()
    })
  })
})
