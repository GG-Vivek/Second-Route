import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from '@/theme'
import { readSource } from '@/test/source'
import { App } from '@/App'
import { WelcomePage } from './WelcomePage'
import { SHOP_WINDOW } from './shopWindow'

/**
 * The landing page (F11.10).
 *
 * It is the first thing a person who has never heard of the product reads,
 * so it has to say what the product does, offer an account and a way in,
 * and open one door for a retailer and one for a buyer. The sections
 * animate as the reader scrolls, which is only allowed to happen when the
 * script is running and the reader has not asked for less motion: the
 * tests below check the page as it is in a browser that cannot animate at
 * all, because that is the page a reader who switches animation off gets.
 */
function renderPage(path = '/welcome') {
  return render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/welcome" element={<WelcomePage />} />
          <Route path="*" element={<p>Elsewhere</p>} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  )
}

/** The part of the stylesheet that starts at `start`, with its braces closed. */
function rule(css: string, start: string): string {
  const from = css.indexOf(start)
  if (from < 0) throw new Error(`the stylesheet does not contain ${start}`)
  const open = css.indexOf('{', from)
  let depth = 0
  for (let i = open; i < css.length; i++) {
    if (css[i] === '{') depth += 1
    else if (css[i] === '}') {
      depth -= 1
      if (depth === 0) return css.slice(from, i + 1)
    }
  }
  throw new Error(`${start} is never closed`)
}

describe('the landing page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
  })

  it('says what the product does before it asks for anything', () => {
    renderPage()

    expect(
      screen.getByRole('heading', { level: 1, name: /one return in/i }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /how a return becomes a decision/i })).toBeInTheDocument()
    expect(screen.getAllByText(/monte carlo/i).length).toBeGreaterThan(0)
  })

  it('offers an account and a way in, at the top and at the bottom', () => {
    renderPage()

    const joins = screen.getAllByRole('link', { name: /create an account/i })
    const enters = screen.getAllByRole('link', { name: /^sign in$/i })

    expect(joins.length).toBeGreaterThanOrEqual(2)
    expect(joins.every((link) => link.getAttribute('href') === '/signup')).toBe(true)
    expect(enters.length).toBeGreaterThanOrEqual(2)
    expect(enters.every((link) => link.getAttribute('href') === '/signin')).toBe(true)
  })

  it('opens one door for a retailer and one for a buyer, each where it says', () => {
    renderPage()

    const retailer = screen.getByRole('link', { name: /create a retailer account/i })
    expect(retailer).toHaveAttribute('href', '/signup/retailer')

    const buyer = screen.getByRole('link', { name: /browse the shop window/i })
    expect(buyer).toHaveAttribute('href', SHOP_WINDOW)
    // It is another site, so it opens as another site: a real link to a
    // real origin, not a route in this application's router.
    expect(buyer).toHaveAttribute('target', '_blank')
    expect(buyer.getAttribute('rel')).toMatch(/noopener/)
    expect(SHOP_WINDOW).toMatch(/^https?:\/\//)
  })

  it('renders the interactive disposition inspection preview with channels and flip condition', () => {
    renderPage()

    expect(screen.getByRole('tablist', { name: /disposition channels/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /refurbish/i })).toBeInTheDocument()
    expect(screen.getByText(/flip condition:/i)).toBeInTheDocument()
  })

  it('writes its sections to reveal themselves as they are scrolled to', () => {
    renderPage()

    expect(document.querySelectorAll('[data-reveal]').length).toBeGreaterThanOrEqual(4)
  })

  it('is complete when nothing can animate it', () => {
    renderPage()

    // This environment has no IntersectionObserver, which is the same
    // position as a browser where the script never ran: nothing may be
    // armed for the animation, or the section it belongs to is invisible.
    expect(document.querySelectorAll('.reveal-armed')).toHaveLength(0)
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /shop window/i })).toHaveLength(1)
  })

  it('hides nothing when the reader has asked for less motion', () => {
    vi.mocked(window.matchMedia).mockImplementation(
      (query: string) =>
        ({
          matches: query.includes('prefers-reduced-motion'),
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        }) as unknown as MediaQueryList,
    )

    renderPage()

    expect(document.querySelectorAll('.reveal-armed')).toHaveLength(0)
    expect(document.querySelectorAll('[data-reveal]').length).toBeGreaterThanOrEqual(4)
  })

  it('keeps one motion curve, and switches it off for less motion', () => {
    const css = readSource('src/index.css', 'frontend/src/index.css')
    const reveal = rule(css, '.reveal {')
    const armed = rule(css, '.reveal-armed {')
    const reduced = rule(css, '@media (prefers-reduced-motion: reduce)')

    // One curve, the same one the rest of the application moves on.
    expect(reveal).toContain('var(--transition-timing)')
    expect(armed).toContain('opacity: 0')

    // The stylesheet is the second guarantee: even if something armed the
    // section, a reader who asked for less motion sees it as it is.
    expect(reduced).toContain('.reveal-armed')
    expect(reduced).toContain('opacity: 1')
    expect(reduced).toContain('transform: none')
  })
})

describe('the route', () => {
  it('opens the landing page at /welcome', () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={['/welcome']}>
          <App />
        </MemoryRouter>
      </ThemeProvider>,
    )

    expect(screen.getByRole('heading', { level: 1, name: /one return in/i })).toBeInTheDocument()
  })
})
