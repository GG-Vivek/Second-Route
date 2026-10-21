import { useId, type ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface FieldProps {
  /** The text above the control. */
  label: string
  /** The control itself. */
  children: (props: { id: string; describedBy?: string }) => ReactNode
  /** A message under the control. */
  hint?: ReactNode
  /** A message under the control that says it is wrong. */
  error?: string | null
  /** Marks the field as required, for the label. */
  required?: boolean
  className?: string
}

/**
 * A labelled control.
 *
 * The label, the hint and the error are wired together with the right
 * identifiers, so a screen reader announces the error with the field rather
 * than on its own.
 */
export function Field({ label, children, hint, error, required, className }: FieldProps) {
  const id = useId()
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(' ')

  return (
    <div className={cn('space-y-2', className)}>
      <label htmlFor={id} className="text-sm font-medium">
        {label}
        {required && (
          <span className="ml-1 text-destructive" aria-hidden="true">
            *
          </span>
        )}
        {required && <span className="sr-only"> (required)</span>}
      </label>

      {children({ id, describedBy: describedBy || undefined })}

      {hint && !error && (
        <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

export const inputClass =
  'w-full rounded-xl border border-input bg-background px-3 py-2 text-sm shadow-xs ' +
  'transition-colors placeholder:text-muted-foreground ' +
  'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/30 focus-visible:outline-none ' +
  'disabled:cursor-not-allowed disabled:opacity-50 ' +
  'aria-invalid:border-destructive aria-invalid:ring-destructive/20'

export const selectClass = `${inputClass} appearance-none bg-no-repeat pr-9`

export const textareaClass = `${inputClass} min-h-[5rem] resize-y leading-relaxed`
