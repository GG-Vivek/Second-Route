import { Meter } from '@/components/ui'

export interface ConfidenceBarProps {
  /** Confidence of the recommendation, between 0 and 1. */
  confidence: number
  /** The threshold the confidence is compared against. */
  threshold?: number
  /** Whether the confidence gate produced a SAFE_DEFAULT. */
  fallbackUsed?: boolean
  className?: string
}

/**
 * The confidence.
 *
 * The gate is drawn on the track, so the number can be read against its
 * threshold without doing the subtraction. When the gate fired, the
 * confidence did not decide anything and the bar says so.
 */
export function ConfidenceBar({
  confidence,
  threshold = 0.7,
  fallbackUsed = false,
  className,
}: ConfidenceBarProps) {
  return (
    <Meter
      value={confidence}
      threshold={threshold}
      tone={fallbackUsed ? 'warning' : 'auto'}
      className={className}
      description={
        fallbackUsed
          ? `Threshold ${(threshold * 100).toFixed(0)}% - below it, routed to the safest channel.`
          : `Threshold ${(threshold * 100).toFixed(0)}%.`
      }
    />
  )
}
