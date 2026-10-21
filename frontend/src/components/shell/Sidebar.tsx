import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { PanelLeftClose, PanelLeft } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Logo } from '@/components/shell/Logo'
import { navigation } from '@/components/shell/navigation'

const COLLAPSE_KEY = 'secondroute-sidebar-collapsed'

export interface SidebarProps {
  /** Called when a destination is chosen, so a mobile sheet can close. */
  onNavigate?: () => void
  className?: string
}

/**
 * The sidebar.
 *
 * Two hundred and eighty eight pixels wide, and forty eight when it is
 * collapsed. The active item is a lime half-pill that hugs the content
 * edge, which is the pmndrs way of saying "you are here" without a
 * colour change on the text.
 */
export function Sidebar({ onNavigate, className }: SidebarProps) {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem(COLLAPSE_KEY) === 'true')
    } catch {
      // A browser that will not store the preference keeps the wide sidebar.
    }
  }, [])

  const toggle = () => {
    setCollapsed((current) => {
      const next = !current
      try {
        window.localStorage.setItem(COLLAPSE_KEY, String(next))
      } catch {
        // The sidebar still collapses for this session.
      }
      return next
    })
  }

  return (
    <aside
      className={cn(
        'flex h-dvh shrink-0 flex-col border-r border-border bg-surface-2/40',
        collapsed ? 'w-sidebar-rail' : 'w-sidebar',
        'transition-[width] duration-200 ease-linear',
        className
      )}
      data-collapsed={collapsed ? 'true' : 'false'}
      data-testid="sidebar"
    >
      <div
        className={cn(
          'flex h-header shrink-0 items-center gap-2 border-b border-border',
          collapsed ? 'justify-center px-2' : 'px-6'
        )}
      >
        <Link
          to="/"
          onClick={onNavigate}
          className="flex items-center gap-2 text-primary"
          aria-label="SecondRoute, home"
        >
          <Logo />
          {!collapsed && <span className="text-base font-semibold tracking-tight">SecondRoute</span>}
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto py-4" aria-label="The main sections">
        <ul className={cn('space-y-1', collapsed ? 'px-2' : 'px-4')}>
          {navigation.map((item) => {
            const active =
              item.href === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.href)
            const Icon = item.icon

            return (
              <li key={item.href}>
                <Link
                  to={item.href}
                  onClick={onNavigate}
                  title={collapsed ? item.name : undefined}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'flex items-center gap-3 rounded-none rounded-r-full py-2.5 text-sm',
                    'text-muted-foreground transition-colors hover:bg-lime-container/40 hover:text-foreground',
                    collapsed ? 'justify-center px-0' : 'px-4',
                    active && 'bg-lime-container font-medium text-on-primary-container'
                  )}
                >
                  <Icon className="size-4 shrink-0" aria-hidden="true" />
                  {!collapsed && <span className="truncate">{item.name}</span>}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className={cn('border-t border-border p-2', collapsed && 'flex justify-center')}>
        <button
          type="button"
          onClick={toggle}
          className={cn(
            'flex items-center gap-3 rounded-2xl px-3 py-2 text-sm text-muted-foreground',
            'transition-colors hover:bg-accent hover:text-foreground',
            collapsed ? 'justify-center px-0' : 'w-full'
          )}
          aria-label={collapsed ? 'Widen the sidebar' : 'Narrow the sidebar'}
          aria-pressed={collapsed}
        >
          {collapsed ? (
            <PanelLeft className="size-4" aria-hidden="true" />
          ) : (
            <>
              <PanelLeftClose className="size-4 shrink-0" aria-hidden="true" />
              <span>Narrow the sidebar</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}
