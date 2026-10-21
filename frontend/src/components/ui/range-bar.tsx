import { cn } from '@/utils/cn'
import { formatMoney } from '@/types/decision'

export interface RangeBarProps {
  /** The low end of the range. */
  low: number
  /** The middle of the range. */
  mid: number
  /** The high end of the range. */
  high: number
  /** The labels under the three marks. */
  labels?: [string, string, string]
  /** A caption above the bar. */
  label?: string
  /** The value the range is compared against, drawn as a second mark. */
  compare?: number
  className?: string
}

/**
 * The range bar.
 *
 * A distribution drawn as a band with a marker in the middle. It is used
 * for the net value of a channel and for the interval of a backtest, which
 * are the same shape of fact.
 */
export function RangeBar({
  low,
  mid,
  high,
  labels = ['p10', 'p50', 'p90'],
  label,
  compare,
  className,
}: RangeBarProps) {
  const min = Math.min(low, mid, high)
  const max = Math.max(low, mid, high)
  const span = max - min
  const position = (value: number) => (span > 0 ? ((value - min) / span) * 100 : 50)

  const lowPosition = position(low)
  const highPosition = position(high)

  return (
    <div className={cn('space-y-2', className)}>
      {label && <p className="text-sm font-medium">{label}</p>}

      <div className="relative h-6">
        <div className="absolute inset-x-0 top-2 h-2 rounded-full bg-muted" />
        <div
          className="absolute top-2 h-2 rounded-full bg-primary/30"
          style={{
            left: `${lowPosition}%`,
            width: `${Math.max(highPosition - lowPosition, 1)}%`,
          }}
          aria-hidden="true"
        />
        <div
          className="absolute top-1 h-4 w-px bg-foreground"
          style={{ left: `${position(mid)}%` }}
          aria-hidden="true"
        />
        {compare !== undefined && (
          <div
            className="absolute top-0.5 h-5 w-0.5 -translate-x-1/2 rounded-full bg-lime-container"
            style={{ left: `${position(compare)}%` }}
            title="Compared against"
            aria-hidden="true"
          />
        )}
      </div>

      <div className="flex items-center justify-between gap-4 font-mono text-xs text-muted-foreground">
        <span>
          {labels[0]} {formatMoney(low)}
        </span>
        <span>
          {labels[1]} {formatMoney(mid)}
        </span>
        <span>
          {labels[2]} {formatMoney(high)}
        </span>
      </div>
    </div>
  )
}
