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
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui'

export default function AnalyticsPage() {
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
      <div className="flex items-center justify-center py-24" data-testid="analytics-loading">
        <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden="true" />
        <span className="ml-2 text-sm text-muted-foreground">Loading the analytics...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div
        className="flex items-center gap-2 rounded-4xl border border-destructive/40 bg-destructive/5 p-4 text-sm"
        data-testid="analytics-error"
      >
        <AlertCircle className="size-4 text-destructive" aria-hidden="true" />
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

      <div className="grid gap-6 xl:grid-cols-2">
        <NorthStarPanel
          section={kind === 'synthetic' ? (northStar?.synthetic ?? EMPTY_NORTH_STAR) : (northStar?.real ?? EMPTY_NORTH_STAR)}
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

      <Card>
        <CardHeader>
          <CardTitle>Export</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            The exports carry the snapshot hash and the model version, so they can be checked
            against the data they came from.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {(['decisions', 'overrides', 'outcomes'] as const).map((entity) => (
              <Button
                key={entity}
                variant="outline"
                size="sm"
                onClick={() => {
                  window.location.href = exportUrl(entity)
                }}
                data-testid={`export-${entity}`}
              >
                <Download className="size-4" aria-hidden="true" />
                {entity}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
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
