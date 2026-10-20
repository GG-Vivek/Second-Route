import { useMemo } from 'react'
import { BarChart3, FlaskConical, TrendingUp } from 'lucide-react'
import { cn } from '@/utils/cn'
import { formatMoney, formatPercent } from '@/types/decision'
import type {
  CalibrationBin,
  NorthStarSection,
  OverrideRateSection,
  RegretBucket,
} from '@/types/decision'

/** Which kind of data a panel is showing. */
export type DataKind = 'synthetic' | 'real'

interface DataKindBadgeProps {
  kind: DataKind
  className?: string
}

/** The badge that says whether the numbers are synthetic or real. */
export function DataKindBadge({ kind, className }: DataKindBadgeProps) {
  const synthetic = kind === 'synthetic'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium',
        synthetic ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800',
        className
      )}
      data-testid={`data-kind-${kind}`}
    >
      {synthetic ? (
        <FlaskConical className="h-3 w-3" aria-hidden="true" />
      ) : (
        <TrendingUp className="h-3 w-3" aria-hidden="true" />
      )}
      {synthetic ? 'Synthetic data' : 'Real data'}
    </span>
  )
}

interface NorthStarPanelProps {
  section: NorthStarSection
  kind: DataKind
  baselineChannel: string
}

/** The north star: the net recovered per return, above the baseline. */
export function NorthStarPanel({
  section,
  kind,
  baselineChannel,
}: NorthStarPanelProps) {
  return (
    <section
      aria-labelledby={`north-star-${kind}`}
      className="rounded-lg border bg-card p-4"
      data-testid={`north-star-${kind}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`north-star-${kind}`} className="font-semibold">
          North star
        </h3>
        <DataKindBadge kind={kind} />
      </div>

      <p className="mt-1 text-sm text-muted-foreground">
        The net recovered per return, against the {baselineChannel} baseline.
      </p>

      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <div>
          <dt className="text-xs text-muted-foreground">Net recovered per return</dt>
          <dd className="font-mono text-xl font-semibold" data-testid="net-recovered">
            {formatMoney(section.net_recovered_per_return)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Baseline per return</dt>
          <dd className="font-mono text-xl font-semibold">{formatMoney(section.baseline_per_return)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Above baseline per return</dt>
          <dd
            className={cn(
              'font-mono text-xl font-semibold',
              section.above_baseline_per_return >= 0 ? 'text-emerald-600' : 'text-red-600'
            )}
            data-testid="above-baseline"
          >
            {formatMoney(section.above_baseline_per_return)}
          </dd>
        </div>
      </dl>

      <p className="mt-3 text-xs text-muted-foreground">
        {section.returns_count} returns. The baseline was tried for{' '}
        {section.observed_baseline_count} of them and taken from the model for{' '}
        {section.estimated_baseline_count}.
      </p>
    </section>
  )
}

interface RegretChartProps {
  buckets: RegretBucket[]
  kind: DataKind
}

/** The mean regret of every period. */
export function RegretChart({ buckets, kind }: RegretChartProps) {
  const largest = useMemo(
    () => Math.max(...buckets.map((bucket) => bucket.mean_regret), 0),
    [buckets]
  )

  return (
    <section
      aria-labelledby={`regret-over-time-${kind}`}
      className="rounded-lg border bg-card p-4"
      data-testid={`regret-over-time-${kind}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`regret-over-time-${kind}`} className="font-semibold">
          Regret over time
        </h3>
        <DataKindBadge kind={kind} />
      </div>

      {buckets.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground" data-testid="no-regret-buckets">
          No regret has been recorded yet.
        </p>
      ) : (
        <ul className="mt-4 space-y-2">
          {buckets.map((bucket) => (
            <li key={bucket.period} className="flex items-center gap-3">
              <span className="w-20 shrink-0 font-mono text-xs text-muted-foreground">
                {bucket.period}
              </span>
              <span className="h-3 flex-1 overflow-hidden rounded bg-muted">
                <span
                  className="block h-full bg-primary"
                  style={{
                    width: largest > 0 ? `${(bucket.mean_regret / largest) * 100}%` : '0%',
                  }}
                />
              </span>
              <span className="w-24 shrink-0 text-right font-mono text-xs">
                {formatMoney(bucket.mean_regret)}
                <span className="block text-muted-foreground">
                  {bucket.observed_count} observed, {bucket.estimated_count} estimated
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

interface CalibrationChartProps {
  bins: CalibrationBin[]
  kind: DataKind
  ece: number
}

/** The reliability curve: the predicted confidence against the observed rate. */
export function CalibrationChart({ bins, kind, ece }: CalibrationChartProps) {
  return (
    <section
      aria-labelledby={`calibration-${kind}`}
      className="rounded-lg border bg-card p-4"
      data-testid={`calibration-${kind}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`calibration-${kind}`} className="font-semibold">
          Calibration
        </h3>
        <DataKindBadge kind={kind} />
      </div>

      <p className="mt-1 text-sm text-muted-foreground">
        Expected calibration error:{' '}
        <span className="font-mono font-semibold" data-testid="ece">
          {ece.toFixed(4)}
        </span>
      </p>

      {bins.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">Nothing to measure yet.</p>
      ) : (
        <table className="mt-4 w-full text-sm">
          <caption className="sr-only">The reliability curve</caption>
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th scope="col" className="py-1">
                Confidence
              </th>
              <th scope="col" className="py-1">
                Predicted
              </th>
              <th scope="col" className="py-1">
                Observed
              </th>
              <th scope="col" className="py-1">
                Count
              </th>
            </tr>
          </thead>
          <tbody>
            {bins.map((bin) => (
              <tr key={`${bin.lower}-${bin.upper}`} className="border-t">
                <td className="py-1 font-mono text-xs">
                  {bin.lower.toFixed(1)} - {bin.upper.toFixed(1)}
                </td>
                <td className="py-1 font-mono text-xs">{bin.mean_predicted.toFixed(2)}</td>
                <td className="py-1 font-mono text-xs">{bin.observed_frequency.toFixed(2)}</td>
                <td className="py-1 font-mono text-xs">{bin.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

interface OverrideRatePanelProps {
  section: OverrideRateSection
  kind: DataKind
}

/** The override rate and the reasons behind it. */
export function OverrideRatePanel({ section, kind }: OverrideRatePanelProps) {
  return (
    <section
      aria-labelledby={`override-rate-${kind}`}
      className="rounded-lg border bg-card p-4"
      data-testid={`override-rate-${kind}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`override-rate-${kind}`} className="font-semibold">
          Override rate
        </h3>
        <DataKindBadge kind={kind} />
      </div>

      <p className="mt-1 text-sm text-muted-foreground">
        <span className="font-mono font-semibold" data-testid="override-rate">
          {formatPercent(section.override_rate)}
        </span>{' '}
        of {section.decisions_count} decisions were overridden.
      </p>

      {section.by_reason.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">No overrides were recorded.</p>
      ) : (
        <ul className="mt-4 space-y-2">
          {section.by_reason.map((reason) => (
            <li key={reason.reason} className="flex items-center justify-between gap-3 text-sm">
              <span className="truncate">{reason.reason}</span>
              <span className="shrink-0 font-mono text-xs text-muted-foreground">
                {reason.count} ({formatPercent(reason.share)})
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

interface AnalyticsHeaderProps {
  /** The kind of data the page is showing. */
  kind: DataKind
  onKindChange: (kind: DataKind) => void
}

/** The switch between the synthetic and the real data. */
export function AnalyticsHeader({ kind, onKindChange }: AnalyticsHeaderProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <BarChart3 className="h-5 w-5" aria-hidden="true" />
          Analytics
        </h2>
        <p className="text-sm text-muted-foreground">
          The synthetic and the real data are shown separately and are never added together.
        </p>
      </div>
      <div
        className="flex rounded-lg border p-1"
        role="group"
        aria-label="Which data to show"
      >
        {(['synthetic', 'real'] as DataKind[]).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => onKindChange(option)}
            aria-pressed={kind === option}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
              kind === option ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'
            )}
            data-testid={`kind-${option}`}
          >
            {option === 'synthetic' ? 'Synthetic' : 'Real'}
          </button>
        ))}
      </div>
    </div>
  )
}
