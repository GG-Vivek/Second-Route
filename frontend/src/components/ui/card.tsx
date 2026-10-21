import type { HTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

/**
 * The card.
 *
 * A 26px radius, a soft shadow and a hairline ring. The ring is what makes
 * the edge readable on a dark surface, so the shadow is only there to lift
 * the card off the page.
 */

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'group/card flex flex-col gap-6 overflow-hidden rounded-4xl bg-card py-6',
        'text-sm text-card-foreground shadow-md ring-1 ring-foreground/5',
        'dark:ring-foreground/10',
        className
      )}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-col gap-1.5 px-6', className)} {...props} />
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('font-heading text-base font-medium leading-none', className)} {...props} />
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-muted-foreground', className)} {...props} />
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('px-6', className)} {...props} />
}

export function CardFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex items-center gap-3 px-6', className)} {...props} />
  )
}
