import { Menu, Plus, Search } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button, Kbd } from '@/components/ui'
import { ThemeToggle } from '@/components/shell/ThemeToggle'
import { OfflineIndicator } from '@/components/shell/OfflineIndicator'

export interface TopbarProps {
  onOpenPalette: () => void
  onOpenNavigation: () => void
}

/**
 * The header.
 *
 * A sticky bar of glass over the page, with a hairline under it. The
 * search trigger is a button rather than an input, because it opens the
 * palette rather than filtering anything on its own.
 */
export function Topbar({ onOpenPalette, onOpenNavigation }: TopbarProps) {
  const navigate = useNavigate()

  return (
    <header className="sticky top-0 z-40 border-b border-border/50 bg-background/95 backdrop-blur-xl">
      <div className="flex h-header items-center gap-3 px-4 lg:px-8">
        <button
          type="button"
          onClick={onOpenNavigation}
          className="flex size-9 items-center justify-center rounded-2xl text-muted-foreground transition-colors hover:bg-accent hover:text-foreground lg:hidden"
          aria-label="Open the navigation"
        >
          <Menu className="size-4" aria-hidden="true" />
        </button>

        <button
          type="button"
          onClick={onOpenPalette}
          className="group flex h-9 min-w-0 flex-1 items-center gap-2 rounded-2xl border border-border bg-card px-3 text-sm text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground sm:max-w-md"
          aria-label="Search the application"
        >
          <Search className="size-4 shrink-0" aria-hidden="true" />
          <span className="flex-1 truncate text-left">Search for anything</span>
          <span className="hidden items-center gap-1 sm:flex">
            <Kbd>⌘</Kbd>
            <Kbd>K</Kbd>
          </span>
        </button>

        <div className="ml-auto flex items-center gap-2">
          <OfflineIndicator className="hidden md:inline-flex" />
          <ThemeToggle />
          <Button
            size="sm"
            onClick={() => navigate('/intake/new')}
            className="hidden sm:inline-flex"
          >
            <Plus className="size-4" aria-hidden="true" />
            New return
          </Button>
        </div>
      </div>
    </header>
  )
}
