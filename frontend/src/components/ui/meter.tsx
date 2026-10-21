import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'
import { formatPercent } from '@/types/decision'

export interface MeterProps {
  /** The measured value, between 0 and 1. */
  value: number
  /** The label above the meter. */
  label?: string
  /** Where the gate is. The marker shows it. */
  threshold?: number
  /** The text under the meter. */
  description?: ReactNode
  /** The tone of the fill. */
  tone?: 'auto' | 'primary' | 'warning' | 'destructive'
  className?: string
}

function toneFor(value: number, threshold: number, tone: MeterProps['tone']): string {
  if (tone === 'primary') return 'bg-primary'
  if (tone === 'warning') return 'bg-warning'
  if (tone === 'destructive') return 'bg-destructive'
  if (value >= 0.85) return 'bg-lime-container'
  if (value >= threshold) return 'bg-cyan-container'
  return 'bg-warning-container'
}

/**
 * The meter.
 *
 * A single value against a gate, which is what the confidence is. The gate
 * is drawn on the track, so a number can be read against its threshold
 * without doing the subtraction.
 */
export function Meter({
  value,
  label = 'Confidence',
  threshold = 0.7,
  description,
  tone = 'auto',
  className,
}: MeterProps) {
  const clamped = Math.max(0, Math.min(1, value))
  const thresholdPercent = Math.max(0, Math.min(1, threshold)) * 100

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between gap-4">
        <span className="text-sm font-medium">{label}</span>
        <span className="font-mono text-sm font-semibold tabular">{formatPercent(clamped)}</span>
      </div>

      <div
        className="relative h-2 w-full overflow-hidden rounded-full bg-muted"
        role="meter"
        aria-valuenow={Math.round(clamped * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} ${formatPercent(clamped)}`}
      >
        <div
          className={cn('h-full rounded-full transition-all', toneFor(clamped, threshold, tone))}
          style={{ width: `${clamped * 100}%` }}
        />
        <div
          className="absolute inset-y-0 w-px bg-foreground/40"
          style={{ left: `${thresholdPercent}%` }}
          aria-hidden="true"
        />
      </div>

      {description && <p className="text-xs text-muted-foreground">{description}</p>}
    </div>
  )
}
