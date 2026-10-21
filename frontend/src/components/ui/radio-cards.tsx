import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

/**
 * The radio cards.
 *
 * A radio group where each option is a card. It is used for the return
 * reason, the order channel and the cosmetic grade, where the operator
 * should be able to see the whole set at once and pick.
 */
export interface RadioCardOption<T extends string> {
  value: T
  label: string
  description?: string
  icon?: ReactNode
  disabled?: boolean
}

export interface RadioCardsProps<T extends string> {
  /** The name of the group. Every card in a group shares it. */
  name: string
  /** The accessible name of the group. */
  label: string
  /** The chosen value. */
  value: T
  /** Called with the newly chosen value. */
  onChange: (value: T) => void
  options: RadioCardOption<T>[]
  /** The direction the cards run in. */
  orientation?: 'horizontal' | 'vertical'
  className?: string
  /** The test id of the group, so a test can find it. */
  'data-testid'?: string
}

export function RadioCards<T extends string>({
  name,
  label,
  value,
  onChange,
  options,
  orientation = 'vertical',
  className,
  ...rest
}: RadioCardsProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      data-testid={rest['data-testid']}
      className={cn(
        'grid gap-3',
        orientation === 'horizontal' ? 'sm:grid-cols-2 lg:grid-cols-3' : 'sm:grid-cols-2',
        className
      )}
    >
      {options.map((option) => {
        const selected = option.value === value
        return (
          <label
            key={option.value}
            className={cn(
              'group/card relative flex cursor-pointer items-center gap-3 rounded-2xl border p-4',
              'transition-colors',
              selected
                ? 'border-primary bg-primary/5 text-foreground'
                : 'border-border bg-card text-foreground hover:border-outline hover:bg-accent/40',
              option.disabled && 'cursor-not-allowed opacity-50'
            )}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={selected}
              disabled={option.disabled}
              onChange={() => onChange(option.value)}
              className="peer sr-only"
            />
            {option.icon && (
              <span
                className={cn(
                  'flex size-9 shrink-0 items-center justify-center rounded-xl transition-colors',
                  selected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                )}
                aria-hidden="true"
              >
                {option.icon}
              </span>
            )}
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium">{option.label}</span>
              {option.description && (
                <span className="mt-0.5 block text-xs text-muted-foreground">
                  {option.description}
                </span>
              )}
            </span>
            <span
              className={cn(
                'flex size-4 shrink-0 items-center justify-center rounded-full border transition-colors',
                selected ? 'border-primary bg-primary' : 'border-outline'
              )}
              aria-hidden="true"
            >
              {selected && <span className="size-1.5 rounded-full bg-primary-foreground" />}
            </span>
          </label>
        )
      })}
    </div>
  )
}
