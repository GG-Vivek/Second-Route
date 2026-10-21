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
 *
 * The coloured badges use the brand tone as the background and the tone
 * that belongs on it as the text. The bright container tones cannot carry
 * text: in the dark theme a bright yellow with white text on it is a ratio
 * of about one and a half to one, which is not a colour anybody can read.
 */
const VARIANTS: Record<BadgeVariant, string> = {
  default: 'bg-primary text-primary-foreground',
  secondary: 'bg-secondary text-secondary-foreground',
  outline: 'border border-border text-foreground',
  destructive: 'bg-destructive/10 text-destructive dark:bg-destructive/20',
  lime: 'bg-lime text-lime-on',
  teal: 'bg-teal text-teal-on',
  cyan: 'bg-cyan text-cyan-on',
  purple: 'bg-purple text-purple-on',
  orange: 'bg-orange text-orange-on',
  yellow: 'bg-yellow text-yellow-on',
  red: 'bg-red text-red-on',
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
