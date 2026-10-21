import { useTheme } from '@/theme'
import { Moon, Sun } from 'lucide-react'
import { Tooltip } from '@/components/ui'

export interface ThemeToggleProps {
  className?: string
}

/**
 * The theme toggle.
 *
 * It switches between the two themes that are on screen. Following the
 * operating system is offered in the command palette, where it belongs,
 * because it is a setting rather than a button.
 */
export function ThemeToggle({ className }: ThemeToggleProps) {
  const { resolvedTheme, setPreference } = useTheme()
  const next = resolvedTheme === 'dark' ? 'light' : 'dark'

  return (
    <Tooltip content={next === 'dark' ? 'Dark mode' : 'Light mode'}>
      <button
        type="button"
        onClick={() => setPreference(next)}
        className={`flex size-9 items-center justify-center rounded-2xl border border-transparent text-muted-foreground transition-colors hover:bg-accent hover:text-foreground ${className ?? ''}`}
        aria-label={next === 'dark' ? 'Switch to dark mode' : 'Switch to light mode'}
        data-testid="theme-toggle"
      >
        {resolvedTheme === 'dark' ? (
          <Sun className="size-4" aria-hidden="true" />
        ) : (
          <Moon className="size-4" aria-hidden="true" />
        )}
      </button>
    </Tooltip>
  )
}
