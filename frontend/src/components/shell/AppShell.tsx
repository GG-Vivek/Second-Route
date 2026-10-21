import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Plus, SunMoon } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useTheme } from '@/theme'
import { Sheet } from '@/components/ui'
import { Sidebar } from '@/components/shell/Sidebar'
import { Topbar } from '@/components/shell/Topbar'
import { CommandPalette } from '@/components/shell/CommandPalette'
import { navigation, type Command } from '@/components/shell/navigation'

export interface AppShellProps {
  children: ReactNode
}

/**
 * The application shell.
 *
 * A sidebar, a glass header and the page. The command palette is bound to
 * the whole application, so everything is reachable from the keyboard
 * without the pointer.
 */
export function AppShell({ children }: AppShellProps) {
  const { preference, setPreference } = useTheme()
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  const commands = useMemo<Command[]>(
    () => [
      ...navigation.map((item) => ({
        id: `go-${item.href}`,
        label: item.name,
        hint: item.description,
        icon: item.icon,
        to: item.href,
        keywords: [item.href],
      })),
      {
        id: 'new-intake',
        label: 'Log a new return',
        hint: 'Record a unit that has come back.',
        icon: Plus,
        to: '/intake/new',
        keywords: ['intake', 'new', 'unit', 'return'],
      },
      {
        id: 'theme',
        label:
          preference === 'system'
            ? 'Follow the system theme'
            : preference === 'dark'
              ? 'Use the light theme'
              : 'Use the dark theme',
        hint: 'Change how the application looks.',
        icon: SunMoon,
        action: () => {
          setPreference(preference === 'system' ? 'dark' : preference === 'dark' ? 'light' : 'system')
        },
        keywords: ['theme', 'dark', 'light', 'system', 'appearance'],
      },
    ],
    [preference, setPreference]
  )

  // The palette opens from anywhere with the keyboard.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() !== 'k') return
      if (!(event.metaKey || event.ctrlKey)) return
      event.preventDefault()
      setPaletteOpen((current) => !current)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <div className="flex min-h-dvh bg-background">
      <Sidebar className="hidden lg:flex" />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onOpenPalette={() => setPaletteOpen(true)}
          onOpenNavigation={() => setMobileNavOpen(true)}
        />

        <main className="flex-1 px-4 py-8 lg:px-8">
          <div className="mx-auto w-full max-w-7xl">{children}</div>
        </main>

        <footer className="border-t border-border px-4 py-4 lg:px-8">
          <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
            <p>SecondRoute. One return in, one disposition instruction out.</p>
            <p className="font-mono">v0.1.0</p>
          </div>
        </footer>
      </div>

      {/* The navigation, as a sheet, on a narrow screen. */}
      <Sheet
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
        title="Go to"
        side="left"
        className="max-w-[18rem] p-0"
      >
        <Sidebar
          onNavigate={() => setMobileNavOpen(false)}
          className={cn('h-full w-full border-r-0 bg-transparent')}
        />
      </Sheet>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        commands={commands}
      />
    </div>
  )
}
