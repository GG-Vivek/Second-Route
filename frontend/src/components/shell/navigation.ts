import {
  BarChart3,
  Boxes,
  FlaskConical,
  HeartPulse,
  LayoutDashboard,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  /** The name shown in the sidebar. */
  name: string
  /** Where it goes. */
  href: string
  /** The icon beside the name. */
  icon: LucideIcon
  /** What the page is for. Shown in the palette and on the mobile sheet. */
  description: string
}

/**
 * The destinations.
 *
 * The order is the order an operator moves in them: what is happening now,
 * what came in, what it was worth, and then the pages that describe the
 * system rather than the work.
 */
export const navigation: NavItem[] = [
  {
    name: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
    description: 'The north star, the live state and the work waiting.',
  },
  {
    name: 'Units',
    href: '/units',
    icon: Boxes,
    description: 'Every returned unit, its inspection and its decision.',
  },
  {
    name: 'Backtest',
    href: '/backtest',
    icon: FlaskConical,
    description: 'Replay past decisions against the baseline policy.',
  },
  {
    name: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
    description: 'What the engine recovered, and how wrong it was.',
  },
  {
    name: 'Health',
    href: '/status',
    icon: HeartPulse,
    description: 'The services, the data sources and their freshness.',
  },
]

export interface Command {
  /** A stable identifier, used as the key and as the test id. */
  id: string
  /** What the command is called. */
  label: string
  /** A sentence saying what it does. */
  hint?: string
  /** The icon beside the label. */
  icon?: LucideIcon
  /** Where it goes, when it goes somewhere. */
  to?: string
  /** What it does, when it does something. */
  action?: () => void
  /** The keyboard shortcut, shown on the right. */
  shortcut?: string
  /** The words that make it easier to find. */
  keywords?: string[]
}

/** The words the palette searches for. */
export function matchesCommand(command: Command, query: string): boolean {
  const needle = query.trim().toLowerCase()
  if (!needle) return true

  const haystack = [command.label, command.hint ?? '', ...(command.keywords ?? [])]
    .join(' ')
    .toLowerCase()

  return haystack.includes(needle)
}
