import { cn } from '@/utils/cn'
import { formatMoney } from '@/types/decision'
import { RangeBar } from '@/components/ui'

export interface NetRangeProps {
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

/**
 * The net value range.
 *
 * The band is the distribution the engine sampled, with the median marked
 * in the middle. The expected value and the gap to the runner-up sit
 * underneath it, because those are the two numbers an operator quotes.
 */
export function NetRange({
  p10,
  p50,
  p90,
  mean,
  runnerUpMean,
  label = 'Net value range',
  className,
}: NetRangeProps) {
  const delta = mean !== undefined && runnerUpMean !== undefined ? mean - runnerUpMean : undefined

  return (
    <div className={cn('space-y-3', className)}>
      <RangeBar low={p10} mid={p50} high={p90} label={label} />

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
        {mean !== undefined && (
          <span>
            Expected <span className="font-mono text-foreground">{formatMoney(mean)}</span>
          </span>
        )}
        {delta !== undefined && (
          <span>
            {delta >= 0 ? '+' : ''}
            <span className="font-mono text-foreground">{formatMoney(delta)}</span> against the
            runner-up
          </span>
        )}
      </div>
    </div>
  )
}
