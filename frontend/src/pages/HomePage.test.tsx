import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { HomePage } from './HomePage'
import { getHealth } from '@/api/health'
import { getNorthStar } from '@/api/decision'

vi.mock('@/api/health', () => ({
  getHealth: vi.fn(),
}))

vi.mock('@/api/decision', () => ({
  getNorthStar: vi.fn(),
}))

const mockGetHealth = vi.mocked(getHealth)
const mockGetNorthStar = vi.mocked(getNorthStar)

const HEALTHY = {
  status: 'healthy' as const,
  version: '0.1.0',
  environment: 'development',
  checks: { database: 'ok' as const, redis: 'ok' as const },
}

const NORTH_STAR = {
  synthetic: {
    returns_count: 12,
    net_recovered_total: 1200,
    baseline_total: 600,
    net_recovered_per_return: 100,
    baseline_per_return: 50,
    above_baseline_per_return: 50,
    observed_baseline_count: 6,
    estimated_baseline_count: 6,
  },
  real: {
    returns_count: 0,
    net_recovered_total: 0,
    baseline_total: 0,
    net_recovered_per_return: 0,
    baseline_per_return: 0,
    above_baseline_per_return: 0,
    observed_baseline_count: 0,
    estimated_baseline_count: 0,
  },
  baseline_channel: 'RECYCLE',
}

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetNorthStar.mockResolvedValue(NORTH_STAR)
  })

  it('shows the north star', async () => {
    mockGetHealth.mockResolvedValue(HEALTHY)
    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('net-recovered')).toHaveTextContent('$100.00')
    })
    expect(screen.getByTestId('above-baseline')).toHaveTextContent('$50.00')
  })

  it('says when the numbers are synthetic', async () => {
    mockGetHealth.mockResolvedValue(HEALTHY)
    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Synthetic data')).toBeInTheDocument()
    })
  })

  it('prefers the real numbers when there are any', async () => {
    mockGetHealth.mockResolvedValue(HEALTHY)
    mockGetNorthStar.mockResolvedValue({
      ...NORTH_STAR,
      real: {
        ...NORTH_STAR.real,
        returns_count: 4,
        net_recovered_per_return: 220,
        baseline_per_return: 150,
        above_baseline_per_return: 70,
      },
    })

    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('net-recovered')).toHaveTextContent('$220.00')
    })
    expect(screen.queryByText('Synthetic data')).not.toBeInTheDocument()
  })

  it('lists the services and their state', async () => {
    mockGetHealth.mockResolvedValue(HEALTHY)
    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('The API')).toBeInTheDocument()
    })
    expect(screen.getByText('The database')).toBeInTheDocument()
    expect(screen.getByText('The cache')).toBeInTheDocument()
  })

  it('says when a service is down', async () => {
    mockGetHealth.mockResolvedValue({
      ...HEALTHY,
      status: 'degraded',
      checks: { database: 'ok', redis: 'failed' },
    })

    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      // The cache is down. The API and the database answered, so they are up.
      expect(screen.getAllByLabelText('Down').length).toBe(1)
    })
  })

  it('says when the service cannot be reached', async () => {
    mockGetHealth.mockRejectedValue(new Error('Network error'))
    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/could not be reached/i)).toBeInTheDocument()
    })
  })

  it('offers the work that is waiting', async () => {
    mockGetHealth.mockResolvedValue(HEALTHY)
    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Log a return')).toBeInTheDocument()
    })
    expect(screen.getByText('Inspect and decide')).toBeInTheDocument()
  })
})
