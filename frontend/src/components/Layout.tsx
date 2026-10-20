import { Outlet, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, HeartPulse, FlaskConical, BarChart3 } from 'lucide-react'
import { cn } from '@/utils/cn'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Units', href: '/units', icon: LayoutDashboard },
  { name: 'Backtest', href: '/backtest', icon: FlaskConical },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Health', href: '/health', icon: HeartPulse },
]

export function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="container mx-auto px-4">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-8">
              <Link to="/" className="flex items-center gap-2 font-semibold text-xl text-primary">
                <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
                SecondRoute
              </Link>
              <nav className="hidden md:flex items-center gap-1">
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={cn(
                      'flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                      location.pathname === item.href
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                    )}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.name}
                  </Link>
                ))}
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-xs text-muted-foreground hidden sm:block">
                v0.1.0
              </span>
            </div>
          </div>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-border bg-background/50">
        <div className="container mx-auto px-4 py-4 text-center text-sm text-muted-foreground">
          SecondRoute - One return in. One disposition instruction out.
        </div>
      </footer>
    </div>
  )
}