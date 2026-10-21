import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface StepsProps {
  children: ReactNode
  className?: string
}

/**
 * The steps.
 *
 * The step numbers hang off a hairline rule on the left, so that a long
 * form reads as a sequence rather than as a wall of fields.
 */
export function Steps({ children, className }: StepsProps) {
  return (
    <ol
      className={cn(
        'space-y-8 md:relative md:ml-4 md:border-l md:border-border md:pl-8 md:space-y-10',
        className
      )}
    >
      {children}
    </ol>
  )
}

export interface StepProps {
  /** The number of the step. */
  number: number
  /** The heading of the step. */
  title: string
  /** A sentence saying what the step is for. */
  description?: string
  children?: ReactNode
  className?: string
}

/**
 * One step.
 *
 * The number is in a ring, in a monospaced face, because a step is a
 * position in a sequence and not a heading.
 */
export function Step({ number, title, description, children, className }: StepProps) {
  return (
    <li className={cn('relative', className)}>
      <span
        className="absolute -left-[3.25rem] flex size-9 items-center justify-center rounded-full border-4 border-background bg-surface-3 font-mono text-base font-medium text-muted-foreground"
        aria-hidden="true"
      >
        {number}
      </span>
      <h3 className="font-heading text-lg font-medium tracking-tight">{title}</h3>
      {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      {children && <div className="mt-4">{children}</div>}
    </li>
  )
}

export interface StickyActionsProps {
  children: ReactNode
  className?: string
}

/**
 * The action bar.
 *
 * It sticks to the bottom of the window while a long form scrolls, so
 * that the button that finishes the work is always within reach.
 */
export function StickyActions({ children, className }: StickyActionsProps) {
  return (
    <div
      className={cn(
        'sticky bottom-0 z-20 -mx-4 mt-8 border-t border-border bg-background/95 px-4 py-4 backdrop-blur-xl',
        'flex flex-wrap items-center gap-3',
        className
      )}
    >
      {children}
    </div>
  )
}
