import { Link } from 'react-router-dom'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@design-system/theme'

/**
 * The header of the shop window.
 *
 * A shop window has no navigation to speak of: there is the window, and
 * there is the search. The theme toggle is here because the reader may
 * want the other one.
 */
export function StorefrontHeader() {
  const { resolvedTheme, setPreference } = useTheme()
  const dark = resolvedTheme === 'dark'

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-4">
        <Link
          to="/"
          className="flex items-center gap-2 text-sm font-semibold tracking-tight"
        >
          <span
            aria-hidden="true"
            className="grid size-7 place-items-center rounded-lg bg-lime-container text-on-lime-container"
          >
            <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor">
              <path
                d="M4 17h6l2-6 3 9 2-6h3"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          SecondRoute
        </Link>

        <span className="hidden text-xs text-muted-foreground sm:inline">
          Inspected and priced
        </span>

        <div className="flex-1" />

        <button
          type="button"
          onClick={() => setPreference(dark ? 'light' : 'dark')}
          className="grid size-9 place-items-center rounded-full text-muted-foreground ring-1 ring-border transition-colors hover:text-foreground"
          aria-label={dark ? 'Switch to the light theme' : 'Switch to the dark theme'}
        >
          {dark ? (
            <Sun className="size-4" aria-hidden="true" />
          ) : (
            <Moon className="size-4" aria-hidden="true" />
          )}
        </button>
      </div>
    </header>
  )
}
