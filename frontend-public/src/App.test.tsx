import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@design-system/theme'
import { App } from '@/App'

vi.mock('@/api/listings', () => ({
  getListings: vi.fn(),
  getListing: vi.fn(),
}))

const { getListings, getListing } = await import('@/api/listings')

/** The shop window itself: a theme, a query client and a route. */
function renderWindow(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  )
}

/**
 * The backdrop, and where it is allowed to be (F11.8).
 *
 * The mesh gradient was a page rather than a place: the window itself had
 * it and the page for one device did not, so a buyer who clicked through
 * dropped out of the room the window was in. It belongs to the frame, not
 * to either page, and both routes sit on it.
 */
describe('the frame of the shop window', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getListings).mockResolvedValue({
      items: [],
      total: 0,
      limit: 24,
      offset: 0,
      families: [],
      categories: [],
      synthetic: true,
    })
    vi.mocked(getListing).mockRejectedValue(new Error('not fetched'))
  })

  it('sits on the animated backdrop, behind the window', () => {
    renderWindow('/')

    expect(document.querySelector('[data-testid^="shader-"]')).not.toBeNull()
  })

  it('sits on it on a device page too, so a buyer never drops out of the room', () => {
    renderWindow('/device/device-1')

    const backdrop = document.querySelector('[data-testid^="shader-"]')
    expect(backdrop).not.toBeNull()
    expect(backdrop).toHaveAttribute('aria-hidden', 'true')
  })
})
