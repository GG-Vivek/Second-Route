import type { ReactNode } from 'react'
import { Check } from 'lucide-react'
import { cn } from '@/utils/cn'

export interface CheckboxOption {
  key: string
  label: string
  description?: string
  icon?: ReactNode
}

export interface CheckboxGroupProps {
  /** The chosen keys. */
  value: Record<string, boolean>
  /** Called with the new map when one box is toggled. */
  onChange: (value: Record<string, boolean>) => void
  options: CheckboxOption[]
  /** The name of the group. */
  name: string
  className?: string
  'data-testid'?: string
}

/**
 * The checkbox group.
 *
 * The functional tests and the accessories on the inspection form. A box
 * that is ticked says so at a glance, which matters when the person filling
 * the form is looking at the device rather than at the screen.
 */
export function CheckboxGroup({
  value,
  onChange,
  options,
  name,
  className,
  ...rest
}: CheckboxGroupProps) {
  return (
    <div
      role="group"
      data-testid={rest['data-testid']}
      className={cn('grid gap-3 sm:grid-cols-2 lg:grid-cols-3', className)}
    >
      {options.map((option) => {
        const checked = Boolean(value[option.key])
        return (
          <label
            key={option.key}
            className={cn(
              'group/card flex cursor-pointer items-center gap-3 rounded-2xl border p-3 transition-colors',
              checked
                ? 'border-primary bg-primary/5 text-foreground'
                : 'border-border bg-card hover:border-outline hover:bg-accent/40'
            )}
          >
            <input
              type="checkbox"
              name={name}
              checked={checked}
              onChange={(event) =>
                onChange({ ...value, [option.key]: event.target.checked })
              }
              className="peer sr-only"
            />
            <span
              className={cn(
                'flex size-5 shrink-0 items-center justify-center rounded-md border transition-colors',
                checked ? 'border-primary bg-primary text-primary-foreground' : 'border-outline'
              )}
              aria-hidden="true"
            >
              {checked && <Check className="size-3" />}
            </span>
            {option.icon && (
              <span className="text-muted-foreground" aria-hidden="true">
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
          </label>
        )
      })}
    </div>
  )
}
