import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AnalyticsPage from '@/pages/AnalyticsPage'
import {
  DataKindBadge,
  NorthStarPanel,
  OverrideRatePanel,
  RegretChart,
} from '@/components/analytics/AnalyticsPanels'
import type {
  NorthStarSection,
  OverrideRateSection,
  RegretBucket,
} from '@/types/decision'

const mockNorthStar = {
  synthetic: {
    returns_count: 10,
    net_recovered_total: 9000,
    baseline_total: 1000,
    net_recovered_per_return: 900,
    baseline_per_return: 100,
    above_baseline_per_return: 800,
    observed_baseline_count: 4,
    estimated_baseline_count: 6,
  },
  real: {
    returns_count: 2,
    net_recovered_total: 1200,
    baseline_total: 200,
    net_recovered_per_return: 600,
    baseline_per_return: 100,
    above_baseline_per_return: 500,
    observed_baseline_count: 1,
    estimated_baseline_count: 1,
  },
  baseline_channel: 'RECYCLE',
}

const mockRegret = {
  bucket: 'month',
  synthetic: [
    {
      period: '2026-09',
      count: 5,
      mean_regret: 120,
      observed_count: 3,
      estimated_count: 2,
      observed_mean_regret: 100,
      estimated_mean_regret: 160,
    },
  ],
  real: [],
}

const mockCalibration = {
  bins: [
    {
      lower: 0.7,
      upper: 0.8,
      count: 10,
      mean_predicted: 0.75,
      observed_frequency: 0.8,
      gap: 0.05,
    },
  ],
  ece: 0.05,
  sample_size: 10,
  bin_count: 10,
  active_version: null,
}

const mockOverrideRate = {
  synthetic: {
    decisions_count: 10,
    overrides_count: 2,
    override_rate: 0.2,
    by_reason: [{ reason: 'Too risky', count: 2, share: 1 }],
  },
  real: {
    decisions_count: 2,
    overrides_count: 0,
    override_rate: 0,
    by_reason: [],
  },
}

vi.mock('@/api/decision', () => ({
  getNorthStar: vi.fn(),
  getRegretOverTime: vi.fn(),
  getCalibration: vi.fn(),
  getOverrideRate: vi.fn(),
  exportUrl: (entity: string) => `/api/v1/export/${entity}`,
}))

import {
  getCalibration,
  getNorthStar,
  getOverrideRate,
  getRegretOverTime,
} from '@/api/decision'

const mockedNorthStar = vi.mocked(getNorthStar)
const mockedRegret = vi.mocked(getRegretOverTime)
const mockedCalibration = vi.mocked(getCalibration)
const mockedOverrideRate = vi.mocked(getOverrideRate)

describe('AnalyticsPanels', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows the synthetic badge for synthetic data', () => {
    render(<DataKindBadge kind="synthetic" />)
    expect(screen.getByTestId('data-kind-synthetic')).toHaveTextContent('Synthetic data')
  })

  it('shows the real badge for real data', () => {
    render(<DataKindBadge kind="real" />)
    expect(screen.getByTestId('data-kind-real')).toHaveTextContent('Real data')
  })

  it('shows the north star of the section it is given', () => {
    const section: NorthStarSection = mockNorthStar.synthetic
    render(<NorthStarPanel section={section} kind="synthetic" baselineChannel="RECYCLE" />)

    expect(screen.getByTestId('net-recovered')).toHaveTextContent('$900.00')
    expect(screen.getByTestId('above-baseline')).toHaveTextContent('$800.00')
    expect(screen.getByTestId('data-kind-synthetic')).toBeInTheDocument()
  })

  it('shows the regret of every period', () => {
    const buckets: RegretBucket[] = mockRegret.synthetic
    render(<RegretChart buckets={buckets} kind="synthetic" />)

    expect(screen.getByText('2026-09')).toBeInTheDocument()
    expect(screen.getByText('$120.00')).toBeInTheDocument()
  })

  it('says when there is no regret yet', () => {
    render(<RegretChart buckets={[]} kind="real" />)
    expect(screen.getByTestId('no-regret-buckets')).toBeInTheDocument()
  })

  it('shows the override rate and the reasons', () => {
    const section: OverrideRateSection = mockOverrideRate.synthetic
    render(<OverrideRatePanel section={section} kind="synthetic" />)

    expect(screen.getByTestId('override-rate')).toHaveTextContent('20.0%')
    expect(screen.getByText('Too risky')).toBeInTheDocument()
  })
})

describe('AnalyticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedNorthStar.mockResolvedValue(mockNorthStar)
    mockedRegret.mockResolvedValue(mockRegret)
    mockedCalibration.mockResolvedValue(mockCalibration)
    mockedOverrideRate.mockResolvedValue(mockOverrideRate)
  })

  function renderPage() {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AnalyticsPage />
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  it('renders every chart', async () => {
    renderPage()

    expect(await screen.findByTestId('north-star-synthetic')).toBeInTheDocument()
    expect(screen.getByTestId('regret-over-time-synthetic')).toBeInTheDocument()
    expect(screen.getByTestId('calibration-synthetic')).toBeInTheDocument()
    expect(screen.getByTestId('override-rate-synthetic')).toBeInTheDocument()
  })

  it('shows the synthetic badge for a synthetic-only dataset', async () => {
    renderPage()

    await screen.findByTestId('north-star-synthetic')
    expect(screen.getAllByTestId('data-kind-synthetic').length).toBeGreaterThan(0)
    expect(screen.queryByTestId('data-kind-real')).not.toBeInTheDocument()
  })

  it('shows the calibration error', async () => {
    renderPage()

    await screen.findByTestId('calibration-synthetic')
    expect(screen.getByTestId('ece')).toHaveTextContent('0.0500')
  })
})
