import { useId } from 'react'
import { cn } from '@/utils/cn'

export interface LogoProps {
  /** The size of the mark in pixels. */
  size?: number
  className?: string
  /** Whether to render organic liquid wobble (liquid-logo inspired). */
  liquid?: boolean
}

/**
 * The mark.
 *
 * Five squares in a cross, which is the pmndrs shape. The centre square is
 * the lime one, so the mark reads as a decision in the middle of a grid.
 * When liquid is enabled, the edges subtly wobble like liquid metal.
 */
export function Logo({ size = 28, className, liquid = true }: LogoProps) {
  const id = useId().replace(/:/g, '')
  const filterId = `sr-logo-liquid-${id}`

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className={cn(
        'shrink-0 overflow-visible transition-transform duration-300 ease-out hover:scale-105',
        className
      )}
      role="img"
      aria-label="SecondRoute"
    >
      {liquid && (
        <defs>
          <filter id={filterId} x="-20%" y="-20%" width="140%" height="140%">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.05"
              numOctaves="1"
              seed="3"
              result="wobble"
            >
              <animate
                attributeName="baseFrequency"
                values="0.045;0.075;0.045"
                dur="7s"
                repeatCount="indefinite"
              />
            </feTurbulence>
            <feDisplacementMap
              in="SourceGraphic"
              in2="wobble"
              scale={size * 0.1}
              xChannelSelector="R"
              yChannelSelector="G"
            />
          </filter>
        </defs>
      )}
      <g filter={liquid ? `url(#${filterId})` : undefined}>
        <g fill="currentColor" opacity="0.35">
          <rect x="1" y="11" width="10" height="10" rx="2" />
          <rect x="11" y="1" width="10" height="10" rx="2" />
          <rect x="11" y="21" width="10" height="10" rx="2" />
          <rect x="21" y="11" width="10" height="10" rx="2" />
        </g>
        <rect
          x="11"
          y="11"
          width="10"
          height="10"
          rx="2"
          fill="rgb(var(--primary))"
          style={{ filter: 'drop-shadow(0 0 4px rgb(var(--primary) / 0.5))' }}
        />
      </g>
    </svg>
  )
}
