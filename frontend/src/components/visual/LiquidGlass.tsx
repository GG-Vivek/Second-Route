import { useId, type MouseEvent, type ReactNode } from 'react'
import { cn } from '@/utils/cn'

/**
 * The liquid glass surfaces and the liquid logo (F11.6).
 *
 * Inspired by liquid-glass-js and liquid-logo. A glass surface bends
 * what is behind it: a turbulence pattern drives a displacement map, which is
 * applied to the backdrop where the browser allows it. Where it does not, the
 * surface is still a frosted panel, which is the part that matters for reading.
 *
 * Moving the pointer across a glass panel creates an interactive specular
 * reflection that tracks the cursor, creating the illusion of light moving
 * through physical frosted glass.
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
 * A panel of frosted glass with interactive specular sheen (liquid-glass-js inspired).
 * The content is ordinary and readable; the glass is the surface behind it.
 */
export function GlassPanel({ children, className, refract = false }: GlassPanelProps) {
  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    e.currentTarget.style.setProperty('--mouse-x', `${x}px`)
    e.currentTarget.style.setProperty('--mouse-y', `${y}px`)
  }

  return (
    <div
      onMouseMove={handleMouseMove}
      className={cn(
        'glass-panel relative overflow-hidden rounded-2xl group transition-all duration-300',
        refract && 'glass-refract',
        className,
      )}
    >
      <div aria-hidden="true" className="glass-specular pointer-events-none absolute inset-0" />
      {children}
    </div>
  )
}

export interface LiquidLogoProps {
  size?: number
  className?: string
}

/**
 * The mark, with its edges moving like a liquid (liquid-logo inspired).
 * The square at the centre is the lime one, with a subtle fluid radiance.
 */
export function LiquidLogo({ size = 28, className }: LiquidLogoProps) {
  const id = useId().replace(/:/g, '')
  const filterId = `sr-liquid-logo-${id}`
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className={cn(
        'shrink-0 overflow-visible transition-transform duration-500 ease-out hover:scale-110',
        className,
      )}
      role="img"
      aria-label="SecondRoute"
    >
      <defs>
        <filter id={filterId} x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves="1" seed="2" result="wobble">
            <animate attributeName="baseFrequency" values="0.05;0.085;0.05" dur="6s" repeatCount="indefinite" />
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
        <rect
          x="11"
          y="11"
          width="10"
          height="10"
          rx="2"
          fill="rgb(var(--primary))"
          style={{ filter: 'drop-shadow(0 0 4px rgb(var(--primary) / 0.6))' }}
        />
      </g>
    </svg>
  )
}
