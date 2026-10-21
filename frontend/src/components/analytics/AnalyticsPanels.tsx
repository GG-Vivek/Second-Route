import { useMemo } from 'react'
import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  XAxis,
  YAxis,
} from 'recharts'
import { BarChart3, FlaskConical, TrendingUp } from 'lucide-react'
import { cn } from '@/utils/cn'
import { formatMoney, formatPercent } from '@/types/decision'
import type {
  CalibrationBin,
  NorthStarSection,
  OverrideRateSection,
  RegretBucket,
} from '@/types/decision'
import { Badge, Card, CardContent, CardHeader, CardTitle, Tabs, TabsList, TabsTrigger } from '@/components/ui'

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
    <Badge
      variant={synthetic ? 'yellow' : 'lime'}
      className={className}
      data-testid={`data-kind-${kind}`}
    >
      {synthetic ? (
        <FlaskConical className="size-3" aria-hidden="true" />
      ) : (
        <TrendingUp className="size-3" aria-hidden="true" />
      )}
      {synthetic ? 'Synthetic data' : 'Real data'}
    </Badge>
  )
}

interface NorthStarPanelProps {
  section: NorthStarSection
  kind: DataKind
  baselineChannel: string
}

/**
 * The north star.
 *
 * The value recovered from a return, against what the baseline policy
 * would have recovered from the same return.
 */
export function NorthStarPanel({
  section,
  kind,
  baselineChannel,
}: NorthStarPanelProps) {
  return (
    <Card aria-labelledby={`north-star-title-${kind}`} data-testid={`north-star-${kind}`}>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle id={`north-star-title-${kind}`}>North star</CardTitle>
        <DataKindBadge kind={kind} />
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          The net recovered per return, against the {baselineChannel} baseline.
        </p>

        <dl className="mt-4 grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-muted-foreground">Net recovered per return</dt>
            <dd className="font-mono text-2xl font-semibold" data-testid="net-recovered">
              {formatMoney(section.net_recovered_per_return)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Baseline per return</dt>
            <dd className="font-mono text-2xl font-semibold">
              {formatMoney(section.baseline_per_return)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Above baseline per return</dt>
            <dd
              className={cn(
                'font-mono text-2xl font-semibold',
                section.above_baseline_per_return >= 0 ? 'text-lime' : 'text-destructive'
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
      </CardContent>
    </Card>
  )
}

interface RegretChartProps {
  buckets: RegretBucket[]
  kind: DataKind
}

/**
 * The regret of every period.
 *
 * The chart shows the mean regret; the list underneath it carries the
 * observed and the estimated counts, which is the difference between a
 * number that was measured and a number that was modelled.
 */
export function RegretChart({ buckets, kind }: RegretChartProps) {
  const largest = useMemo(
    () => Math.max(...buckets.map((bucket) => bucket.mean_regret), 0),
    [buckets]
  )

  return (
    <Card aria-labelledby={`regret-over-time-title-${kind}`} data-testid={`regret-over-time-${kind}`}>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle id={`regret-over-time-title-${kind}`}>Regret over time</CardTitle>
        <DataKindBadge kind={kind} />
      </CardHeader>
      <CardContent>
        {buckets.length === 0 ? (
          <p className="py-8 text-sm text-muted-foreground" data-testid="no-regret-buckets">
            No regret has been recorded yet.
          </p>
        ) : (
          <ul className="space-y-3">
            {buckets.map((bucket) => (
              <li key={bucket.period} className="flex items-center gap-3">
                <span className="w-16 shrink-0 font-mono text-xs text-muted-foreground">
                  {bucket.period}
                </span>
                <span className="h-3 flex-1 overflow-hidden rounded-full bg-muted">
                  <span
                    className="block h-full rounded-full bg-primary"
                    style={{
                      width: largest > 0 ? `${(bucket.mean_regret / largest) * 100}%` : '0%',
                    }}
                  />
                </span>
                <span className="w-28 shrink-0 text-right font-mono text-xs">
                  {formatMoney(bucket.mean_regret)}
                  <span className="block text-muted-foreground">
                    {bucket.observed_count} observed, {bucket.estimated_count} estimated
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

interface CalibrationChartProps {
  bins: CalibrationBin[]
  kind: DataKind
  ece: number
}

/**
 * The reliability curve.
 *
 * A prediction of 0.8 should be right about eighty percent of the time.
 * The line is what that looks like when the engine is well calibrated,
 * and the gap between the line and the points is the expected calibration
 * error.
 */
export function CalibrationChart({ bins, kind, ece }: CalibrationChartProps) {
  const points = useMemo(
    () =>
      bins.map((bin) => ({
        predicted: bin.mean_predicted,
        observed: bin.observed_frequency,
        count: bin.count,
      })),
    [bins]
  )

  return (
    <Card aria-labelledby={`calibration-title-${kind}`} data-testid={`calibration-${kind}`}>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle id={`calibration-title-${kind}`}>Calibration</CardTitle>
        <DataKindBadge kind={kind} />
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          Expected calibration error:{' '}
          <span className="font-mono font-semibold" data-testid="ece">
            {ece.toFixed(4)}
          </span>
        </p>

        {bins.length === 0 ? (
          <p className="py-8 text-sm text-muted-foreground">Nothing to measure yet.</p>
        ) : (
          <>
            <div className="mt-4 h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: -16 }}>
                  <CartesianGrid stroke="rgb(var(--border))" strokeDasharray="3 5" />
                  <XAxis
                    type="number"
                    dataKey="predicted"
                    domain={[0, 1]}
                    tick={{ fontSize: 11, fill: 'rgb(var(--muted-foreground))' }}
                    tickFormatter={(value: number) => value.toFixed(1)}
                    stroke="rgb(var(--border))"
                  />
                  <YAxis
                    type="number"
                    dataKey="observed"
                    domain={[0, 1]}
                    tick={{ fontSize: 11, fill: 'rgb(var(--muted-foreground))' }}
                    tickFormatter={(value: number) => value.toFixed(1)}
                    stroke="rgb(var(--border))"
                  />
                  <ReferenceLine
                    segment={[
                      { x: 0, y: 0 },
                      { x: 1, y: 1 },
                    ]}
                    stroke="rgb(var(--muted-foreground))"
                    strokeDasharray="4 4"
                  />
                  <Scatter data={points} fill="rgb(var(--primary))" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>

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
          </>
        )}
      </CardContent>
    </Card>
  )
}

interface OverrideRatePanelProps {
  section: OverrideRateSection
  kind: DataKind
}

/** The override rate and the reasons behind it. */
export function OverrideRatePanel({ section, kind }: OverrideRatePanelProps) {
  const largest = useMemo(
    () => Math.max(...section.by_reason.map((reason) => reason.count), 0),
    [section.by_reason]
  )

  return (
    <Card aria-labelledby={`override-rate-title-${kind}`} data-testid={`override-rate-${kind}`}>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle id={`override-rate-title-${kind}`}>Override rate</CardTitle>
        <DataKindBadge kind={kind} />
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          <span className="font-mono font-semibold" data-testid="override-rate">
            {formatPercent(section.override_rate)}
          </span>{' '}
          of {section.decisions_count} decisions were overridden.
        </p>

        {section.by_reason.length === 0 ? (
          <p className="py-8 text-sm text-muted-foreground">No overrides were recorded.</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {section.by_reason.map((reason) => (
              <li key={reason.reason} className="space-y-1">
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate">{reason.reason}</span>
                  <span className="shrink-0 font-mono text-xs text-muted-foreground">
                    {reason.count} ({formatPercent(reason.share)})
                  </span>
                </div>
                <span className="block h-2 overflow-hidden rounded-full bg-muted">
                  <span
                    className="block h-full rounded-full bg-primary"
                    style={{
                      width: largest > 0 ? `${(reason.count / largest) * 100}%` : '0%',
                    }}
                  />
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
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
          <BarChart3 className="size-5" aria-hidden="true" />
          Analytics
        </h2>
        <p className="text-sm text-muted-foreground">
          The synthetic and the real data are shown separately and are never added together.
        </p>
      </div>
      <Tabs
        value={kind}
        onValueChange={(value) => onKindChange(value as DataKind)}
        className="space-y-0"
      >
        <TabsList>
          <TabsTrigger value="synthetic">Synthetic</TabsTrigger>
          <TabsTrigger value="real">Real</TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
  )
}
