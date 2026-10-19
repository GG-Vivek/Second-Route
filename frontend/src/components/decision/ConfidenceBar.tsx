import { cn } from '@/utils/cn'
import { formatPercent } from '@/types/decision'

interface ConfidenceBarProps {
  /** Confidence of the recommendation, between 0 and 1. */
  confidence: number
  /** The threshold the confidence is compared against. */
  threshold?: number
  /** Whether the confidence gate produced a SAFE_DEFAULT. */
  fallbackUsed?: boolean
  className?: string
}

function confidenceTone(confidence: number, fallbackUsed: boolean): string {
  if (fallbackUsed) return 'bg-yellow-500'
  if (confidence >= 0.85) return 'bg-green-500'
  if (confidence >= 0.7) return 'bg-blue-500'
  return 'bg-yellow-500'
}

export function ConfidenceBar({
  confidence,
  threshold = 0.7,
  fallbackUsed = false,
  className,
}: ConfidenceBarProps) {
  const clamped = Math.max(0, Math.min(1, confidence))
  const thresholdPercent = Math.max(0, Math.min(1, threshold)) * 100

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">Confidence</span>
        <span
          className={cn(
            'font-mono font-semibold',
            fallbackUsed ? 'text-yellow-700' : 'text-foreground'
          )}
        >
          {formatPercent(clamped)}
        </span>
      </div>

      <div
        className="relative h-2 w-full overflow-hidden rounded-full bg-muted"
        role="meter"
        aria-valuenow={Math.round(clamped * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Recommendation confidence ${formatPercent(clamped)}`}
      >
        <div
          className={cn('h-full rounded-full transition-all', confidenceTone(clamped, fallbackUsed))}
          style={{ width: `${clamped * 100}%` }}
        />
        <div
          className="absolute inset-y-0 w-0.5 bg-foreground/40"
          style={{ left: `${thresholdPercent}%` }}
          aria-hidden="true"
        />
      </div>

      <p className="text-xs text-muted-foreground">
        Threshold {formatPercent(threshold)}
        {fallbackUsed && ' - below threshold, routed to the safest channel'}
      </p>
    </div>
  )
}
