import { cn } from '@/utils/cn'

export interface LogoProps {
  /** The size of the mark in pixels. */
  size?: number
  className?: string
}

/**
 * The mark.
 *
 * Five squares in a cross, which is the pmndrs shape. The centre square is
 * the lime one, so the mark reads as a decision in the middle of a grid.
 */
export function Logo({ size = 28, className }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className={cn('shrink-0', className)}
      role="img"
      aria-label="SecondRoute"
    >
      <g fill="currentColor" opacity="0.35">
        <rect x="1" y="11" width="10" height="10" rx="2" />
        <rect x="11" y="1" width="10" height="10" rx="2" />
        <rect x="11" y="21" width="10" height="10" rx="2" />
        <rect x="21" y="11" width="10" height="10" rx="2" />
      </g>
      <rect x="11" y="11" width="10" height="10" rx="2" fill="rgb(var(--primary))" />
    </svg>
  )
}
