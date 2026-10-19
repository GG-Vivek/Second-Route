import { cn } from '@/utils/cn'
import { formatMoney } from '@/types/decision'

interface NetRangeProps {
  /** 10th percentile of the net value. */
  p10: number
  /** Median of the net value. */
  p50: number
  /** 90th percentile of the net value. */
  p90: number
  /** Expected net value. */
  mean?: number
  /** Expected net value of the runner-up, used for the delta. */
  runnerUpMean?: number
  label?: string
  className?: string
}

export function NetRange({
  p10,
  p50,
  p90,
  mean,
  runnerUpMean,
  label = 'Net value range',
  className,
}: NetRangeProps) {
  const low = Math.min(p10, p50, p90)
  const high = Math.max(p10, p50, p90)
  const span = high - low
  const position = (value: number) => (span > 0 ? ((value - low) / span) * 100 : 50)

  const delta = mean !== undefined && runnerUpMean !== undefined ? mean - runnerUpMean : undefined

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium">{label}</span>
        {mean !== undefined && (
          <span className="font-mono text-sm text-muted-foreground">
            expected {formatMoney(mean)}
          </span>
        )}
      </div>

      <div className="relative h-8">
        <div className="absolute inset-x-0 top-3 h-2 rounded-full bg-muted" />
        <div
          className="absolute top-3 h-2 rounded-full bg-primary/30"
          style={{
            left: `${position(p10)}%`,
            width: `${Math.max(position(p90) - position(p10), 1)}%`,
          }}
          aria-hidden="true"
        />
        <div
          className="absolute top-1.5 h-5 w-0.5 bg-foreground"
          style={{ left: `${position(p50)}%` }}
          aria-hidden="true"
        />
      </div>

      <div className="flex items-center justify-between font-mono text-xs text-muted-foreground">
        <span>p10 {formatMoney(p10)}</span>
        <span>p50 {formatMoney(p50)}</span>
        <span>p90 {formatMoney(p90)}</span>
      </div>

      {delta !== undefined && (
        <p className="text-xs text-muted-foreground">
          {delta >= 0 ? '+' : ''}
          {formatMoney(delta)} against the runner-up
        </p>
      )}
    </div>
  )
}
