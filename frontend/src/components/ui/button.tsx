import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export type ButtonVariant =
  | 'default'
  | 'secondary'
  | 'outline'
  | 'ghost'
  | 'destructive'
  | 'link'

export type ButtonSize = 'xs' | 'sm' | 'default' | 'lg' | 'icon'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

/**
 * The button.
 *
 * A 26px radius, a hairline focus ring three pixels wide, and a press that
 * nudges the button down by one pixel rather than scaling it. The icon size
 * is set on the button so that every icon inside it is the same size
 * whatever the button's size.
 */
const VARIANTS: Record<ButtonVariant, string> = {
  default: 'bg-primary text-primary-foreground hover:bg-primary/80',
  secondary:
    'bg-secondary text-secondary-foreground hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)]',
  outline:
    'border border-border bg-background hover:bg-muted hover:text-foreground dark:bg-transparent dark:hover:bg-input/30',
  ghost: 'hover:bg-muted hover:text-foreground dark:hover:bg-muted/50',
  destructive:
    'bg-destructive/10 text-destructive hover:bg-destructive/20 dark:bg-destructive/20 dark:hover:bg-destructive/30',
  link: 'text-primary underline-offset-4 hover:underline',
}

const SIZES: Record<ButtonSize, string> = {
  xs: 'h-6 gap-1 px-2.5 text-xs',
  sm: 'h-8 gap-1 px-3',
  default: 'h-9 gap-1.5 px-3',
  lg: 'h-10 gap-1.5 px-4',
  icon: 'size-9',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        'group/button inline-flex shrink-0 select-none items-center justify-center whitespace-nowrap',
        'rounded-4xl border border-transparent bg-clip-padding text-sm font-medium',
        'outline-none transition-all',
        'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/30',
        'active:translate-y-px',
        'disabled:pointer-events-none disabled:opacity-50',
        'aria-invalid:border-destructive aria-invalid:ring-[3px] aria-invalid:ring-destructive/20',
        '[&_svg]:size-4',
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...props}
    />
  )
)
Button.displayName = 'Button'
