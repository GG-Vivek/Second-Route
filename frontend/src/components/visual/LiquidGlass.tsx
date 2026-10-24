import { useId, type ReactNode } from 'react'
import { cn } from '@/utils/cn'

/**
 * The liquid glass surfaces and the liquid logo (F11.6).
 *
 * The references are liquid-glass-js and liquid-logo. A glass surface bends
 * what is behind it: a turbulence pattern drives a displacement map, which is
 * applied to the backdrop where the browser allows it. Where it does not, the
 * surface is still a frosted panel, which is the part that matters for reading.
 *
 * The filter is defined once per page, in `LiquidGlassFilter`, and the glass
 * panels refer to it by name.
 */

/** The shared glass filter. Render it once, near the root of the page. */
export function LiquidGlassFilter() {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      width="0"
      height="0"
      className="pointer-events-none absolute"
    >
      <defs>
        <filter id="sr-liquid-glass" x="0" y="0" width="100%" height="100%">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.008 0.014"
            numOctaves="2"
            seed="7"
            result="noise"
          />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="14" xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </defs>
    </svg>
  )
}

export interface GlassPanelProps {
  children: ReactNode
  className?: string
  /** Bend the backdrop as well as frosting it. Only the hero uses this. */
  refract?: boolean
}

/**
 * A panel of frosted glass. The content is ordinary and readable; the glass
 * is the surface behind it.
 */
export function GlassPanel({ children, className, refract = false }: GlassPanelProps) {
  return (
    <div className={cn('glass-panel rounded-2xl', refract && 'glass-refract', className)}>
      {children}
    </div>
  )
}

export interface LiquidLogoProps {
  size?: number
  className?: string
}

/**
 * The mark, with its edges moving like a liquid. The square at the centre is
 * the lime one, as on the operator console's logo, so the two read as one
 * product.
 */
export function LiquidLogo({ size = 28, className }: LiquidLogoProps) {
  const id = useId().replace(/:/g, '')
  const filterId = `sr-liquid-logo-${id}`
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className={cn('shrink-0 overflow-visible', className)}
      role="img"
      aria-label="SecondRoute"
    >
      <defs>
        <filter id={filterId} x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves="1" seed="2" result="wobble">
            <animate attributeName="baseFrequency" values="0.05;0.09;0.05" dur="7s" repeatCount="indefinite" />
          </feTurbulence>
          <feDisplacementMap in="SourceGraphic" in2="wobble" scale={size * 0.12} xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </defs>
      <g filter={`url(#${filterId})`}>
        <g fill="currentColor" opacity="0.35">
          <rect x="1" y="11" width="10" height="10" rx="2" />
          <rect x="11" y="1" width="10" height="10" rx="2" />
          <rect x="11" y="21" width="10" height="10" rx="2" />
          <rect x="21" y="11" width="10" height="10" rx="2" />
        </g>
        <rect x="11" y="11" width="10" height="10" rx="2" fill="rgb(var(--primary))" />
      </g>
    </svg>
  )
}
