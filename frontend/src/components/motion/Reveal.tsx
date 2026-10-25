import { useLayoutEffect, useRef, useState, type ElementType, type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface RevealProps extends HTMLAttributes<HTMLElement> {
  /** The element the section is drawn as. */
  as?: ElementType
  children: ReactNode
}

/**
 * A section that arrives as the reader scrolls to it (F11.10).
 *
 * The whole mechanism is one class and one observer, with no dependency:
 * the section is given a waiting state, an IntersectionObserver takes it
 * off when the section comes into view, and the transition in the
 * stylesheet does the rest. Nothing here decides how anything moves.
 *
 * Three positions are handled rather than assumed:
 *
 * - No IntersectionObserver (an old browser, or this test environment):
 *   nothing is ever given the waiting state, so nothing is ever hidden.
 * - The reader has asked for less motion: same, nothing is armed. The
 *   stylesheet's own reduced-motion rule is the second line of defence.
 * - The script never ran: the waiting state only ever exists as a class
 *   the script adds, so the section is simply where it was written.
 *
 * One observer is shared by every section on the page. A page has a
 * handful of them and each one stops being watched as soon as it has
 * arrived, so there is nothing here worth allocating per section.
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
      { threshold: 0.2, rootMargin: '0px 0px -6% 0px' },
    )
  }

  return watcher
}

export function Reveal({ as, className, children, ...props }: RevealProps) {
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

  return (
    <Tag
      ref={ref}
      data-reveal=""
      className={cn('reveal', armed && 'reveal-armed', className)}
      {...props}
    >
      {children}
    </Tag>
  )
}
