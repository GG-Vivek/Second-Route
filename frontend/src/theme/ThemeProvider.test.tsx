import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider } from './ThemeProvider'
import { useTheme, type ThemePreference } from './index'

/**
 * The shape of a media query change event, spelled out locally so the
 * test does not depend on a DOM type name being in scope.
 */
interface SchemeChange {
  matches: boolean
  media: string
}

type SchemeListener = (event: SchemeChange) => void

/**
 * A controllable stand-in for the media query list.
 *
 * jsdom has no `matchMedia`, so the global setup mocks it with a stub that
 * always reports `matches: false` and never fires a change. The theme needs
 * both of those behaviours, so this stub lets a test drive them.
 */
function installMatchMedia(initialDark: boolean) {
  const listeners = new Set<SchemeListener>()
  let matches = initialDark

  const list: MediaQueryList = {
    get matches() {
      return matches
    },
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn((_type: string, listener: SchemeListener) => {
      listeners.add(listener)
    }),
    removeEventListener: vi.fn((_type: string, listener: SchemeListener) => {
      listeners.delete(listener)
    }),
    dispatchEvent: vi.fn(),
  } as unknown as MediaQueryList

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation(() => list),
  })

  return {
    list,
    set(next: boolean) {
      matches = next
      const event: SchemeChange = { matches: next, media: list.media }
      for (const listener of listeners) listener(event)
    },
  }
}

/** A button that reports the theme it is looking at. */
function ThemeProbe() {
  const { preference, resolvedTheme, setPreference, toggle } = useTheme()
  return (
    <div>
      <span data-testid="preference">{preference}</span>
      <span data-testid="resolved">{resolvedTheme}</span>
      <button type="button" onClick={() => setPreference('light')}>
        set light
      </button>
      <button type="button" onClick={() => setPreference('dark')}>
        set dark
      </button>
      <button type="button" onClick={() => setPreference('system')}>
        set system
      </button>
      <button type="button" onClick={toggle}>
        toggle
      </button>
    </div>
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    window.localStorage.clear()
    document.documentElement.classList.remove('dark')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('starts light when nothing has been chosen', () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    expect(screen.getByTestId('resolved')).toHaveTextContent('light')
    expect(screen.getByTestId('preference')).toHaveTextContent('light')
  })

  it('leaves the document in the light tokens when nothing has been chosen', () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    expect(document.documentElement).not.toHaveClass('dark')
  })

  it('switches to the dark tokens when the dark theme is chosen', async () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'set dark' }))

    expect(screen.getByTestId('resolved')).toHaveTextContent('dark')
    expect(document.documentElement).toHaveClass('dark')
  })

  it('remembers the choice across a reload', async () => {
    const { unmount } = render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'set light' }))
    unmount()

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    expect(screen.getByTestId('preference')).toHaveTextContent('light')
    expect(screen.getByTestId('resolved')).toHaveTextContent('light')
  })

  it('follows the system preference when the system theme is chosen', () => {
    installMatchMedia(true)

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    act(() => {
      screen.getByRole('button', { name: 'set system' }).click()
    })

    expect(screen.getByTestId('preference')).toHaveTextContent('system')
    expect(screen.getByTestId('resolved')).toHaveTextContent('dark')
  })

  it('reacts when the system preference changes underneath it', () => {
    const media = installMatchMedia(false)

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    act(() => {
      screen.getByRole('button', { name: 'set system' }).click()
    })
    expect(screen.getByTestId('resolved')).toHaveTextContent('light')

    act(() => {
      media.set(true)
    })

    expect(screen.getByTestId('resolved')).toHaveTextContent('dark')
    expect(document.documentElement).toHaveClass('dark')
  })

  it('toggles between light and dark', async () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'toggle' }))
    expect(screen.getByTestId('resolved')).toHaveTextContent('dark')

    await userEvent.click(screen.getByRole('button', { name: 'toggle' }))
    expect(screen.getByTestId('resolved')).toHaveTextContent('light')
  })

  it('survives a browser that refuses to store the preference', async () => {
    const getItem = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage is disabled')
    })
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage is disabled')
    })

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'set light' }))

    // The theme still changes, it just cannot be remembered.
    expect(screen.getByTestId('resolved')).toHaveTextContent('light')
    expect(getItem).toHaveBeenCalled()
    expect(setItem).toHaveBeenCalled()
  })

  it('refuses to be used outside the provider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    expect(() => render(<ThemeProbe />)).toThrow(/ThemeProvider/)

    consoleError.mockRestore()
  })
})

describe('theme preferences', () => {
  it('accepts exactly three preferences', () => {
    const preferences: ThemePreference[] = ['light', 'dark', 'system']
    expect(preferences).toHaveLength(3)
  })
})
