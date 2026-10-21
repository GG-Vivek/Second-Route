import type { ReactNode } from 'react'
import {
  Info,
  Lightbulb,
  MessageSquareWarning,
  OctagonAlert,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/utils/cn'

export type CalloutTone = 'note' | 'tip' | 'important' | 'warning' | 'caution'

export interface CalloutProps {
  /** The role of the message. */
  tone?: CalloutTone
  /** The headline. The body is the children. */
  title?: string
  /** Overrides the icon that goes with the tone. */
  icon?: ReactNode
  children?: ReactNode
  /** The test id. Defaults to the tone. */
  testId?: string
  className?: string
}

const TONES: Record<CalloutTone, { container: string; icon: LucideIcon }> = {
  note: { container: 'bg-note-container text-on-note-container', icon: Info },
  tip: { container: 'bg-tip-container text-on-tip-container', icon: Lightbulb },
  important: {
    container: 'bg-important-container text-on-important-container',
    icon: MessageSquareWarning,
  },
  warning: { container: 'bg-warning-container text-on-warning-container', icon: TriangleAlert },
  caution: { container: 'bg-caution-container text-on-caution-container', icon: OctagonAlert },
}

/**
 * The callout.
 *
 * One component for every message that interrupts the reader: the prototype
 * badge, the offline notice, the restored draft, the look-ahead verdict,
 * the stale source warning. There were five hand-rolled banners before this
 * and each one had its own colours.
 *
 * The container colour is the same in both themes, because a callout is a
 * statement about the state of the world rather than part of the chrome.
 */
export function Callout({
  tone = 'note',
  title,
  icon,
  children,
  testId,
  className,
}: CalloutProps) {
  const Icon = TONES[tone].icon

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-2xl p-4',
        TONES[tone].container,
        className
      )}
      role="note"
      data-testid={testId ?? `callout-${tone}`}
      data-tone={tone}
    >
      <span className="mt-0.5 shrink-0" aria-hidden="true">
        {icon ?? <Icon className="size-4" />}
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className="text-sm [&_p]:leading-relaxed">{children}</div>}
      </div>
    </div>
  )
}
