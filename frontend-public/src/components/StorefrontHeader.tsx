import { Link } from 'react-router-dom'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@design-system/theme'
import { LiquidLogo } from '@design-system/components/visual'

/**
 * The address of the operator console, when the deployment names one.
 *
 * The shop window and the console are two applications. The console's sign-in
 * and sign-up pages are where a retailer or a staff member gets an account, so
 * the window links there. When no address is configured the links are left
 * out, rather than pointing at a place that does not exist.
 */
export const CONSOLE_URL: string = (import.meta.env.VITE_CONSOLE_URL ?? '').replace(/\/$/, '')

/**
 * The header of the shop window.
 *
 * The brand is the liquid mark. The theme toggle is here because a reader may
 * prefer the other theme, and the account links go to the console.
 */
export function StorefrontHeader() {
  const { resolvedTheme, setPreference } = useTheme()
  const dark = resolvedTheme === 'dark'

  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-3.5">
        <Link to="/" className="flex items-center gap-2.5 text-sm font-semibold tracking-tight">
          <LiquidLogo size={26} />
          SecondRoute
        </Link>

        <span className="hidden text-xs text-muted-foreground md:inline">Inspected, priced, ready</span>

        <div className="flex-1" />

        {CONSOLE_URL && (
          <>
            <a
              href={`${CONSOLE_URL}/signin`}
              className="rounded-full px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Sign in
            </a>
            <a
              href={`${CONSOLE_URL}/signup`}
              className="rounded-full bg-primary px-3.5 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/85"
            >
              Create an account
            </a>
          </>
        )}

        <button
          type="button"
          onClick={() => setPreference(dark ? 'light' : 'dark')}
          className="grid size-9 place-items-center rounded-full text-muted-foreground ring-1 ring-border transition-colors hover:text-foreground"
          aria-label={dark ? 'Switch to the light theme' : 'Switch to the dark theme'}
        >
          {dark ? <Sun className="size-4" aria-hidden="true" /> : <Moon className="size-4" aria-hidden="true" />}
        </button>
      </div>
    </header>
  )
}
