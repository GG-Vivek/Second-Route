import { useEffect, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useFocusTrap } from './useFocusTrap'

export interface SheetProps {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  /** Which edge the sheet comes from. */
  side?: 'left' | 'right'
  children?: ReactNode
  footer?: ReactNode
  className?: string
}

/**
 * The sheet.
 *
 * A panel that comes in from the edge of the screen. It behaves like the
 * dialog in every way that matters: it traps the keyboard, closes on
 * escape, and gives the focus back when it closes.
 */
export function Sheet({
  open,
  onClose,
  title,
  description,
  side = 'right',
  children,
  footer,
  className,
}: SheetProps) {
  const [mounted, setMounted] = useState(false)
  const containerRef = useFocusTrap(open, onClose)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!open || !mounted) return null

  return createPortal(
    <div className="fixed inset-0 z-50" role="presentation">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        aria-hidden="true"
        onMouseDown={onClose}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="sheet-title"
        aria-describedby={description ? 'sheet-description' : undefined}
        className={cn(
          'absolute inset-y-0 flex w-full max-w-md flex-col gap-4 overflow-y-auto',
          'border-border bg-popover p-6 text-popover-foreground shadow-2xl',
          side === 'right' ? 'right-0 border-l' : 'left-0 border-r',
          'animate-slide-in-from-top',
          className
        )}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h2 id="sheet-title" className="text-lg font-medium">
              {title}
            </h2>
            {description && (
              <p id="sheet-description" className="text-sm text-muted-foreground">
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="-mr-1 -mt-1 rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            aria-label="Close panel"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>

        {children}

        {footer && <div className="mt-auto flex justify-end gap-2 border-t pt-4">{footer}</div>}
      </div>
    </div>,
    document.body
  )
}
