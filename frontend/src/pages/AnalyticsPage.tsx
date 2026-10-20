import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Download, Loader2 } from 'lucide-react'
import {
  AnalyticsHeader,
  CalibrationChart,
  NorthStarPanel,
  OverrideRatePanel,
  RegretChart,
  type DataKind,
} from '@/components/analytics/AnalyticsPanels'
import {
  exportUrl,
  getCalibration,
  getNorthStar,
  getOverrideRate,
  getRegretOverTime,
} from '@/api/decision'

export function AnalyticsPage() {
  const [kind, setKind] = useState<DataKind>('synthetic')

  const northStarQuery = useQuery({
    queryKey: ['analytics', 'north-star'],
    queryFn: getNorthStar,
  })
  const regretQuery = useQuery({
    queryKey: ['analytics', 'regret-over-time'],
    queryFn: () => getRegretOverTime(),
  })
  const calibrationQuery = useQuery({
    queryKey: ['analytics', 'calibration'],
    queryFn: () => getCalibration(),
  })
  const overrideRateQuery = useQuery({
    queryKey: ['analytics', 'override-rate'],
    queryFn: getOverrideRate,
  })

  const loading =
    northStarQuery.isLoading ||
    regretQuery.isLoading ||
    calibrationQuery.isLoading ||
    overrideRateQuery.isLoading

  const error =
    northStarQuery.error ?? regretQuery.error ?? calibrationQuery.error ?? overrideRateQuery.error

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12" data-testid="analytics-loading">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
        <span className="ml-2 text-sm text-muted-foreground">Loading the analytics...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div
        className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm"
        data-testid="analytics-error"
      >
        <AlertCircle className="h-4 w-4 text-destructive" aria-hidden="true" />
        The analytics could not be loaded.
      </div>
    )
  }

  const northStar = northStarQuery.data
  const regret = regretQuery.data
  const calibration = calibrationQuery.data
  const overrideRate = overrideRateQuery.data

  return (
    <div className="space-y-6">
      <AnalyticsHeader kind={kind} onKindChange={setKind} />

      <div className="grid gap-4 lg:grid-cols-2">
        <NorthStarPanel
          section={
            kind === 'synthetic'
              ? (northStar?.synthetic ?? EMPTY_NORTH_STAR)
              : (northStar?.real ?? EMPTY_NORTH_STAR)
          }
          kind={kind}
          baselineChannel={northStar?.baseline_channel ?? 'RECYCLE'}
        />
        <RegretChart
          buckets={kind === 'synthetic' ? (regret?.synthetic ?? []) : (regret?.real ?? [])}
          kind={kind}
        />
        <CalibrationChart
          bins={calibration?.bins ?? []}
          kind={kind}
          ece={calibration?.ece ?? 0}
        />
        <OverrideRatePanel
          section={
            kind === 'synthetic'
              ? (overrideRate?.synthetic ?? EMPTY_OVERRIDE_RATE)
              : (overrideRate?.real ?? EMPTY_OVERRIDE_RATE)
          }
          kind={kind}
        />
      </div>

      <section aria-labelledby="export-heading" className="rounded-lg border bg-card p-4">
        <h2 id="export-heading" className="font-semibold">
          Export
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          The exports carry the snapshot hash and the model version, so they can be
          checked against the data they came from.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {(['decisions', 'overrides', 'outcomes'] as const).map((entity) => (
            <a
              key={entity}
              href={exportUrl(entity)}
              download
              className="inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium hover:bg-accent"
              data-testid={`export-${entity}`}
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              {entity}
            </a>
          ))}
        </div>
      </section>
    </div>
  )
}

const EMPTY_NORTH_STAR = {
  returns_count: 0,
  net_recovered_total: 0,
  baseline_total: 0,
  net_recovered_per_return: 0,
  baseline_per_return: 0,
  above_baseline_per_return: 0,
  observed_baseline_count: 0,
  estimated_baseline_count: 0,
}

const EMPTY_OVERRIDE_RATE = {
  decisions_count: 0,
  overrides_count: 0,
  override_rate: 0,
  by_reason: [],
}
