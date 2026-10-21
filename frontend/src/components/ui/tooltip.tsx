import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface TooltipProps {
  /** The tooltip text. */
  content: ReactNode
  /** What the tooltip is attached to. */
  children: ReactNode
  /** Which side the tooltip appears on. */
  side?: 'top' | 'bottom'
  className?: string
}

/**
 * The tooltip.
 *
 * It appears on hover and on keyboard focus, so it is not a pointer-only
 * affordance.
 */
export function Tooltip({ content, children, side = 'top', className }: TooltipProps) {
  return (
    <span className={cn('group/tip relative inline-flex', className)}>
      {children}
      <span
        role="tooltip"
        className={cn(
          'pointer-events-none absolute left-1/2 z-50 -translate-x-1/2 whitespace-nowrap',
          'rounded-md bg-foreground px-2 py-1 text-xs text-background',
          'opacity-0 transition-opacity duration-150',
          'group-hover/tip:opacity-100 group-focus-within/tip:opacity-100',
          side === 'top' ? 'bottom-full mb-1.5' : 'top-full mt-1.5'
        )}
      >
        {content}
      </span>
    </span>
  )
}

export interface KbdProps {
  children: ReactNode
  className?: string
}

/** The keyboard key. */
export function Kbd({ children, className }: KbdProps) {
  return (
    <kbd
      className={cn(
        'inline-flex h-5 min-w-5 items-center justify-center rounded-lg bg-muted px-1.5',
        'font-sans text-xs font-medium text-muted-foreground',
        className
      )}
    >
      {children}
    </kbd>
  )
}
