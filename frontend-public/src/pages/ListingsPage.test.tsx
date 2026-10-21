import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { ListingCard } from '@/components/ListingCard'
import { ListingsPage } from '@/pages/ListingsPage'
import type { Listing, ListingPage as ListingPageData } from '@/api/listings'

vi.mock('@/api/listings', () => ({
  getListings: vi.fn(),
  getListing: vi.fn(),
}))

const { getListings } = await import('@/api/listings')

/** One device, for the tests. */
function aListing(overrides: Partial<Listing> = {}): Listing {
  return {
    id: 'device-1',
    title: 'M3 Pro 2023 512',
    family: 'MacBook Pro',
    model_name: 'M3 Pro',
    year: '2023',
    storage_gb: '512',
    ram_gb: '18',
    color: 'Space Gray',
    grade: 'A',
    condition: 'Like new',
    battery_health_pct: '95',
    price: {
      amount: 1499.5,
      currency: 'USD',
      source: 'synthetic',
      as_of: '2026-01-01T00:00:00',
      is_estimate: true,
    },
    photo: { url: '/uploads/one.jpg', alt: 'M3 Pro, 2023' },
    photo_count: 3,
    listed_at: '2026-01-01T00:00:00',
    in_stock: true,
    ...overrides,
  }
}

/** A page of devices. */
function aPage(items: Listing[]): ListingPageData {
  return {
    items,
    total: items.length,
    limit: 24,
    offset: 0,
    families: ['MacBook Pro'],
    synthetic: true,
  }
}

/** The page, in a router and with a query client. */
function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ListingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('a card on the window', () => {
  it('shows the device, its condition and its price', () => {
    render(
      <MemoryRouter>
        <ListingCard listing={aListing()} />
      </MemoryRouter>,
    )

    expect(screen.getByText('M3 Pro 2023 512')).toBeInTheDocument()
    expect(screen.getByText('Like new')).toBeInTheDocument()
    expect(screen.getByText('$1,499.50')).toBeInTheDocument()
    expect(screen.getByText('estimated resale price')).toBeInTheDocument()
  })

  it('links to the device', () => {
    render(
      <MemoryRouter>
        <ListingCard listing={aListing()} />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link')).toHaveAttribute('href', '/device/device-1')
  })

  it('says the price is an estimate', () => {
    render(
      <MemoryRouter>
        <ListingCard listing={aListing()} />
      </MemoryRouter>,
    )

    expect(screen.getByText('estimated resale price')).toBeInTheDocument()
  })
})

describe('the window', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows the devices', async () => {
    vi.mocked(getListings).mockResolvedValue(aPage([aListing()]))
    renderPage()

    await waitFor(() => expect(screen.getByText('M3 Pro 2023 512')).toBeInTheDocument())
    expect(screen.getByText('1 device')).toBeInTheDocument()
  })

  it('says that the prices are modelled', async () => {
    vi.mocked(getListings).mockResolvedValue(aPage([aListing()]))
    renderPage()

    await waitFor(() =>
      expect(screen.getByText('These prices are modelled')).toBeInTheDocument(),
    )
  })

  it('does not say that the prices are modelled when they are not', async () => {
    vi.mocked(getListings).mockResolvedValue({ ...aPage([aListing()]), synthetic: false })
    renderPage()

    await waitFor(() => expect(screen.getByText('M3 Pro 2023 512')).toBeInTheDocument())
    expect(screen.queryByText('These prices are modelled')).not.toBeInTheDocument()
  })

  it('says when nothing is on the window', async () => {
    vi.mocked(getListings).mockResolvedValue(aPage([]))
    renderPage()

    await waitFor(() =>
      expect(screen.getByText('Nothing is on the window')).toBeInTheDocument(),
    )
  })

  it('says when the shop cannot be reached', async () => {
    vi.mocked(getListings).mockRejectedValue(new Error('The shop could not be reached.'))
    renderPage()

    await waitFor(() =>
      expect(screen.getByText('The shop could not be reached')).toBeInTheDocument(),
    )
  })

  it('filters by family', async () => {
    const user = userEvent.setup()
    vi.mocked(getListings).mockResolvedValue(aPage([aListing()]))
    renderPage()

    await waitFor(() => expect(screen.getByText('M3 Pro 2023 512')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'MacBook Pro' }))

    await waitFor(() =>
      expect(vi.mocked(getListings).mock.calls.some((call) => call[0]?.family === 'MacBook Pro')).toBe(
        true,
      ),
    )
  })

  it('searches for a model', async () => {
    const user = userEvent.setup()
    vi.mocked(getListings).mockResolvedValue(aPage([aListing()]))
    renderPage()

    await waitFor(() => expect(screen.getByText('M3 Pro 2023 512')).toBeInTheDocument())
    await user.type(screen.getByLabelText('Search for a model'), 'M3')

    await waitFor(() =>
      expect(
        vi.mocked(getListings).mock.calls.some((call) => call[0]?.search === 'M3'),
      ).toBe(true),
    )
  })
})
