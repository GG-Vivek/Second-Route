import { useEffect, useRef, useState } from 'react'

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

/**
 * Keep the keyboard inside an overlay, and give the focus back when it
 * closes.
 *
 * The focus returns to whatever had it before the overlay opened, so that
 * closing a dialog puts the reader back where they were rather than at the
 * top of the page.
 *
 * The overlay is returned as a callback ref rather than as an object ref,
 * because the overlay often renders into a portal that only appears after
 * the first effect has run. An object ref would be null on that first pass
 * and the trap would never be set up.
 */
export function useFocusTrap(active: boolean, onEscape?: () => void) {
  const [node, setNode] = useState<HTMLDivElement | null>(null)

  // The escape handler is kept in a ref so that a parent passing a new
  // function on every render does not tear the trap down and steal the
  // focus back.
  const escapeRef = useRef(onEscape)
  useEffect(() => {
    escapeRef.current = onEscape
  }, [onEscape])

  useEffect(() => {
    if (!active || !node) return

    const previous = document.activeElement as HTMLElement | null

    const focusable = () =>
      Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (element) =>
          !element.hasAttribute('hidden') && element.getAttribute('aria-hidden') !== 'true'
      )

    // Wait a tick so that the content of the overlay has been laid out and
    // its controls exist before the first one is focused.
    const frame = requestAnimationFrame(() => {
      // Only move the focus if it is not already inside the overlay. The
      // reader may have clicked a field before the frame ran, and taking
      // the focus back would move it out from under them.
      if (node.contains(document.activeElement)) return
      const first = focusable()[0] ?? node
      first.focus()
    })

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        escapeRef.current?.()
        return
      }
      if (event.key !== 'Tab') return

      const items = focusable()
      if (items.length === 0) {
        event.preventDefault()
        return
      }

      const first = items[0]
      const last = items[items.length - 1]

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown, true)

    return () => {
      cancelAnimationFrame(frame)
      document.removeEventListener('keydown', onKeyDown, true)
      previous?.focus?.()
    }
  }, [active, node])

  return setNode
}
