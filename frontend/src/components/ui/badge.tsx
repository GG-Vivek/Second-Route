import type { HTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export type BadgeVariant =
  | 'default'
  | 'secondary'
  | 'outline'
  | 'destructive'
  | 'lime'
  | 'teal'
  | 'cyan'
  | 'purple'
  | 'orange'
  | 'yellow'
  | 'red'

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

/**
 * The badge.
 *
 * Twenty pixels tall with a 22px radius, so it reads as a lozenge rather
 * than as a hairline tag. The prefix of a badge may be dimmed by wrapping
 * it in a span with `opacity-70`.
 */
const VARIANTS: Record<BadgeVariant, string> = {
  default: 'bg-primary text-primary-foreground',
  secondary: 'bg-secondary text-secondary-foreground',
  outline: 'border border-border text-foreground',
  destructive: 'bg-destructive/10 text-destructive dark:bg-destructive/20',
  lime: 'bg-lime-container text-on-primary-container',
  teal: 'bg-teal-container text-teal',
  cyan: 'bg-cyan-container text-cyan',
  purple: 'bg-purple-container text-purple',
  orange: 'bg-orange-container text-orange',
  yellow: 'bg-yellow-container text-yellow',
  red: 'bg-red-container text-red',
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'group/badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1',
        'overflow-hidden whitespace-nowrap rounded-3xl border border-transparent px-2',
        'text-xs font-medium transition-all',
        '[&>svg]:size-3',
        VARIANTS[variant],
        className
      )}
      {...props}
    />
  )
}
