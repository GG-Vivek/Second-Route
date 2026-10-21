import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/utils/cn'

/**
 * The skeleton.
 *
 * A shimmer sweeps across it while the real content is on its way. It is
 * the only moving thing on the page, so it reads as waiting rather than as
 * decoration.
 */
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'tw-shimmer rounded-xl bg-muted/70',
        'bg-[length:200%_100%] bg-no-repeat',
        className
      )}
      {...props}
    />
  )
}

/**
 * A block of skeleton lines.
 *
 * `lines` is how many lines to show. The last one is shorter, so the block
 * has the shape of a paragraph rather than of a rectangle.
 */
export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton
          key={index}
          className={cn('h-3', index === lines - 1 ? 'w-2/3' : 'w-full')}
        />
      ))}
    </div>
  )
}

/**
 * The empty state.
 *
 * Every list that can come back empty says what it is for and what to do
 * next, rather than showing a blank panel.
 */
export interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 rounded-4xl border border-dashed p-12 text-center',
        className
      )}
    >
      {icon && (
        <span className="flex size-12 items-center justify-center rounded-2xl bg-muted text-muted-foreground" aria-hidden="true">
          {icon}
        </span>
      )}
      <div className="space-y-1">
        <p className="font-medium">{title}</p>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  )
}
