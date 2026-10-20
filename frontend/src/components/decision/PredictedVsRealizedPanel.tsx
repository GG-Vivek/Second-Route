import { TrendingUp, TrendingDown, Target, CircleDot } from 'lucide-react'
import { cn } from '@/utils/cn'
import { channelLabel, formatMoney, type PredictedVsRealized } from '@/types/decision'

interface PredictedVsRealizedRowProps {
  comparison: PredictedVsRealized
}

/** One row: what was predicted against what actually happened. */
export function PredictedVsRealizedRow({ comparison }: PredictedVsRealizedRowProps) {
  const beat = comparison.residual > 0
  const withinBand = comparison.in_range

  return (
    <div
      className="rounded-lg border bg-card p-4"
      data-testid={`comparison-${comparison.outcome_id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium">
            {channelLabel(comparison.channel)}
            {!comparison.used_recommended && (
              <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-800">
                Overrode {channelLabel(comparison.recommended_channel)}
              </span>
            )}
          </p>
          <p className="text-xs text-muted-foreground">
            Recommended: {channelLabel(comparison.recommended_channel)}
          </p>
        </div>

        <span
          className={cn(
            'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium',
            withinBand
              ? 'bg-green-100 text-green-800'
              : comparison.below_p10
                ? 'bg-red-100 text-red-800'
                : 'bg-yellow-100 text-yellow-800'
          )}
          data-testid="in-range-badge"
        >
          <CircleDot className="h-3 w-3" aria-hidden="true" />
          {withinBand
            ? 'Inside predicted range'
            : comparison.below_p10
              ? 'Below p10'
              : 'Above p90'}
        </span>
      </div>

      <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-xs text-muted-foreground">Predicted range</dt>
          <dd className="font-mono text-sm">
            {formatMoney(comparison.predicted.p10)} – {formatMoney(comparison.predicted.p90)}
          </dd>
          <dd className="font-mono text-xs text-muted-foreground">
            p50 {formatMoney(comparison.predicted.p50)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Realized net</dt>
          <dd className="font-mono text-sm font-semibold">
            {formatMoney(comparison.realized_net)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Residual</dt>
          <dd
            className={cn(
              'flex items-center gap-1 font-mono text-sm',
              beat ? 'text-green-600' : 'text-red-600'
            )}
            data-testid="residual"
          >
            {beat ? (
              <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <TrendingDown className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {formatMoney(comparison.residual)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Absolute residual</dt>
          <dd className="font-mono text-sm">
            {formatMoney(comparison.absolute_residual)}
          </dd>
        </div>
      </dl>
    </div>
  )
}

interface PredictedVsRealizedPanelProps {
  comparisons: PredictedVsRealized[]
  summary?: {
    total: number
    in_range_count: number
    in_range_rate: number
    below_p10_count: number
    above_p90_count: number
    used_recommended_count: number
    mean_residual: number
    mean_absolute_residual: number
  }
  title?: string
}

/** The predicted vs realized panel with a summary header. */
export function PredictedVsRealizedPanel({
  comparisons,
  summary,
  title = 'Predicted vs realized',
}: PredictedVsRealizedPanelProps) {
  if (comparisons.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center" data-testid="no-comparisons">
        <Target className="mx-auto mb-3 h-8 w-8 text-muted-foreground" aria-hidden="true" />
        <p className="font-medium">Nothing to compare yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Record an outcome for a unit to see how the prediction held up.
        </p>
      </div>
    )
  }

  const stats = summary ?? {
    total: comparisons.length,
    in_range_count: comparisons.filter((c) => c.in_range).length,
    in_range_rate:
      comparisons.filter((c) => c.in_range).length / comparisons.length,
    below_p10_count: comparisons.filter((c) => c.below_p10).length,
    above_p90_count: comparisons.filter((c) => c.above_p90).length,
    used_recommended_count: comparisons.filter((c) => c.used_recommended).length,
    mean_residual:
      comparisons.reduce((sum, c) => sum + c.residual, 0) / comparisons.length,
    mean_absolute_residual:
      comparisons.reduce((sum, c) => sum + c.absolute_residual, 0) / comparisons.length,
  }

  return (
    <section aria-labelledby="predicted-vs-realized-heading" className="space-y-4">
      <div>
        <h2 id="predicted-vs-realized-heading" className="text-lg font-semibold">
          {title}
        </h2>
        <p className="text-muted-foreground text-sm">
          What the engine predicted against what actually happened.
        </p>
      </div>

      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border bg-card p-4">
          <dt className="text-xs text-muted-foreground">Outcomes compared</dt>
          <dd className="font-mono text-xl font-semibold">{stats.total}</dd>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <dt className="text-xs text-muted-foreground">Inside predicted range</dt>
          <dd className="font-mono text-xl font-semibold" data-testid="in-range-rate">
            {(stats.in_range_rate * 100).toFixed(0)}%
          </dd>
          <dd className="text-xs text-muted-foreground">
            {stats.in_range_count} of {stats.total}
          </dd>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <dt className="text-xs text-muted-foreground">Mean residual</dt>
          <dd className="font-mono text-xl font-semibold">
            {formatMoney(stats.mean_residual)}
          </dd>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <dt className="text-xs text-muted-foreground">Mean absolute residual</dt>
          <dd className="font-mono text-xl font-semibold">
            {formatMoney(stats.mean_absolute_residual)}
          </dd>
        </div>
      </dl>

      <div className="space-y-3">
        {comparisons.map((comparison) => (
          <PredictedVsRealizedRow key={comparison.outcome_id} comparison={comparison} />
        ))}
      </div>
    </section>
  )
}
