/**
 * Tests for the backtest page (F5.6).
 *
 * The page has to show the interval, not only the point estimate, and it
 * has to say when a run was refused for look-ahead.
 */

import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { BacktestPage } from './BacktestPage'
import { api } from '@/api/client'

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const mockApiGet = vi.mocked(api.get)
const mockApiPost = vi.mocked(api.post)

const RUN = {
  id: 'run-1',
  org_id: 'org-1',
  created_at: '2026-03-01T12:00:00Z',
  name: 'Backtest',
  baseline_name: 'fixed-channel',
  baseline_channel: 'RESELL',
  window_start: '2026-02-01T00:00:00Z',
  window_end: '2026-03-01T00:00:00Z',
  decision_count: 40,
  mean_difference: 12.5,
  ci_lower: 4.0,
  ci_upper: 21.0,
  confidence: 0.95,
  method: 'paired-bootstrap-percentile',
  samples: 2000,
  seed: 0,
  is_synthetic: true,
  report: {
    baseline_name: 'fixed-channel',
    baseline_description: 'Always recommends the same channel.',
    baseline_channel: 'RESELL',
    decision_count: 40,
    skipped: [],
    mean_engine_net: 120.0,
    mean_baseline_net: 107.5,
    mean_difference: 12.5,
    interval: {
      point_estimate: 12.5,
      lower: 4.0,
      upper: 21.0,
      confidence: 0.95,
      method: 'paired-bootstrap-percentile',
      samples: 2000,
      seed: 0,
      n: 40,
      excludes_zero: true,
    },
    confidence: 0.95,
    method: 'paired-bootstrap-percentile',
    win_rate: 0.62,
    channel_breakdown: { LIQUIDATE: { engine: 40, baseline: 0 } },
    lookahead: {
      has_leak: false,
      is_clean: true,
      finding_count: 0,
      findings: [],
    },
    window_start: '2026-02-01T00:00:00Z',
    window_end: '2026-03-01T00:00:00Z',
    warnings: [],
  },
}

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('BacktestPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApiGet.mockResolvedValue([])
  })

  it('renders the form', () => {
    render(<BacktestPage />, { wrapper: createWrapper() })

    expect(screen.getByText('Historical backtest')).toBeInTheDocument()
    expect(screen.getByLabelText(/Organisation id/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Run backtest/i })).toBeInTheDocument()
  })

  it('cannot run without an organisation', () => {
    render(<BacktestPage />, { wrapper: createWrapper() })

    expect(screen.getByRole('button', { name: /Run backtest/i })).toBeDisabled()
  })

  it('shows the difference and its interval after a run', async () => {
    mockApiPost.mockResolvedValue(RUN)
    render(<BacktestPage />, { wrapper: createWrapper() })

    await userEvent.type(screen.getByLabelText(/Organisation id/i), 'org-1')
    await userEvent.click(screen.getByRole('button', { name: /Run backtest/i }))

    await waitFor(() => expect(screen.getByText('40 decision(s) compared')).toBeInTheDocument())

    // The interval is shown, not only the point estimate.
    expect(screen.getByText(/95% interval/i)).toBeInTheDocument()
    expect(screen.getByText('excludes zero')).toBeInTheDocument()
    expect(screen.getByText(/paired-bootstrap-percentile/)).toBeInTheDocument()
  })

  it('says when a run was refused for look-ahead', async () => {
    mockApiPost.mockRejectedValue({
      response: {
        data: {
          detail: {
            message: 'Backtest refused: 1 decision(s) used data dated after they were made',
          },
        },
      },
    })
    render(<BacktestPage />, { wrapper: createWrapper() })

    await userEvent.type(screen.getByLabelText(/Organisation id/i), 'org-1')
    await userEvent.click(screen.getByRole('button', { name: /Run backtest/i }))

    expect(
      await screen.findByText(/Backtest refused: 1 decision\(s\)/)
    ).toBeInTheDocument()
  })

  it('lists the previous runs', async () => {
    mockApiGet.mockResolvedValue([RUN])
    render(<BacktestPage />, { wrapper: createWrapper() })

    await waitFor(() => expect(screen.getByText('Previous runs')).toBeInTheDocument())
    expect(screen.getByText('fixed-channel (RESELL)')).toBeInTheDocument()
  })
})
