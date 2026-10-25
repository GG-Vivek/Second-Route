import { useLayoutEffect, useRef, useState, type ElementType, type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface RevealProps extends HTMLAttributes<HTMLElement> {
  /** The element the section is drawn as. */
  as?: ElementType
  children: ReactNode
  /** Delay in milliseconds for staggered Theatre-style sequence choreography. */
  delay?: number
}

/**
 * A section that arrives as the reader scrolls to it (F11.10).
 *
 * The mechanism is one class and one observer: the section is given a waiting
 * state, an IntersectionObserver takes it off when the section comes into view,
 * and the transition in the stylesheet does the rest.
 *
 * Supports optional `delay` prop for staggered Theatre-style cascade entrances.
 *
 * Three positions are handled:
 * - No IntersectionObserver: nothing is armed, so nothing is ever hidden.
 * - Reader asked for less motion: nothing is armed.
 * - Script never ran: section is simply rendered where it was written.
 */
let watcher: IntersectionObserver | null = null

function sharedWatcher(): IntersectionObserver | null {
  if (typeof window === 'undefined' || typeof window.IntersectionObserver === 'undefined') return null

  if (!watcher) {
    watcher = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          entry.target.classList.add('is-visible')
          watcher?.unobserve(entry.target)
        }
      },
      // A section is revealed when most of it is on the screen, and a
      // little before it reaches the top, so the reader never watches a
      // heading arrive after they have started reading it.
      { threshold: 0.15, rootMargin: '0px 0px -6% 0px' },
    )
  }

  return watcher
}

export function Reveal({ as, className, children, delay, style, ...props }: RevealProps) {
  const Tag = (as ?? 'div') as ElementType
  const ref = useRef<HTMLElement | null>(null)
  const [armed, setArmed] = useState(false)

  useLayoutEffect(() => {
    const element = ref.current
    const observer = sharedWatcher()
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (!element || !observer || reduced) return

    setArmed(true)
    observer.observe(element)
    return () => observer.unobserve(element)
  }, [])

  const combinedStyle = delay
    ? { ...style, transitionDelay: `${delay}ms` }
    : style

  return (
    <Tag
      ref={ref}
      data-reveal=""
      className={cn('reveal', armed && 'reveal-armed', className)}
      style={combinedStyle}
      {...props}
    >
      {children}
    </Tag>
  )
}
