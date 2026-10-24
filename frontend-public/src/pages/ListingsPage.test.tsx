import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@design-system/theme'

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
    title: 'MacBook Pro M3 Pro',
    category: 'laptop',
    category_label: 'Laptops',
    summary: '14.2-inch display · M3 Pro · 70 Wh battery',
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
    categories: [
      { key: 'laptop', label: 'Laptops', count: 1 },
      { key: 'phone', label: 'Phones', count: 2 },
    ],
    synthetic: true,
  }
}

/** The page, in a router and with a query client. */
function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <ListingsPage />
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  )
}

describe('a card on the window', () => {
  it('describes a television by its size, not by a memory figure', () => {
    render(
      <MemoryRouter>
        <ListingCard
          listing={aListing({
            id: 'tv-1',
            title: 'QLED TV QN90C 65-inch',
            category: 'tv',
            category_label: 'TVs',
            summary: '65-inch Neo QLED 4K · 120 Hz',
            ram_gb: '',
            storage_gb: '',
            battery_health_pct: null,
          })}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText('65-inch Neo QLED 4K · 120 Hz')).toBeInTheDocument()
    expect(screen.getByText('TVs')).toBeInTheDocument()
    expect(screen.queryByText(/GB memory/)).not.toBeInTheDocument()
  })


  it('shows the device, its condition and its price', () => {
    render(
      <MemoryRouter>
        <ListingCard listing={aListing()} />
      </MemoryRouter>,
    )

    expect(screen.getByText('MacBook Pro M3 Pro')).toBeInTheDocument()
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

    await waitFor(() => expect(screen.getByText('MacBook Pro M3 Pro')).toBeInTheDocument())
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

    await waitFor(() => expect(screen.getByText('MacBook Pro M3 Pro')).toBeInTheDocument())
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

  it('filters by kind of device', async () => {
    const user = userEvent.setup()
    vi.mocked(getListings).mockResolvedValue(aPage([aListing()]))
    renderPage()

    await waitFor(() => expect(screen.getByText('MacBook Pro M3 Pro')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /Phones/ }))

    await waitFor(() =>
      expect(vi.mocked(getListings).mock.calls.some((call) => call[0]?.category === 'phone')).toBe(
        true,
      ),
    )
  })

  it('waits for the reader to stop typing before it searches', async () => {
    const user = userEvent.setup()
    vi.mocked(getListings).mockResolvedValue(aPage([aListing()]))
    renderPage()

    await waitFor(() => expect(screen.getByText('MacBook Pro M3 Pro')).toBeInTheDocument())
    vi.mocked(getListings).mockClear()
    await user.type(screen.getByLabelText('Search for a model'), 'M3')

    // Two keystrokes inside the delay make at most one search for the final word.
    await waitFor(() =>
      expect(vi.mocked(getListings).mock.calls.some((call) => call[0]?.search === 'M3')).toBe(true),
    )
    expect(vi.mocked(getListings).mock.calls.some((call) => call[0]?.search === 'M')).toBe(false)
  })

  it('searches for a model', async () => {
    const user = userEvent.setup()
    vi.mocked(getListings).mockResolvedValue(aPage([aListing()]))
    renderPage()

    await waitFor(() => expect(screen.getByText('MacBook Pro M3 Pro')).toBeInTheDocument())
    await user.type(screen.getByLabelText('Search for a model'), 'M3')

    await waitFor(() =>
      expect(
        vi.mocked(getListings).mock.calls.some((call) => call[0]?.search === 'M3'),
      ).toBe(true),
    )
  })
})
