import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, FlaskConical, Loader2, ShieldCheck, ShieldAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { createBacktest, listBacktests, type BacktestRun } from '@/api/backtest'
import { formatMoney } from '@/types/decision'

/** The channels the engine can recommend. */
const CHANNELS = ['LIQUIDATE', 'RESELL', 'RECYCLE', 'PARTS_HARVEST', 'DONATE']

/**
 * Show the bootstrap interval as a band around the point estimate.
 *
 * The band is scaled to the wider of the interval and a small floor, so a
 * tight interval is still visible and a wide one does not overflow.
 */
function IntervalBar({
  point,
  lower,
  upper,
}: {
  point: number
  lower: number
  upper: number
}) {
  const span = Math.max(upper - lower, Math.abs(point) * 0.1, 1)
  const min = lower - span * 0.2
  const max = upper + span * 0.2
  const width = max - min
  const position = (value: number) => ((value - min) / width) * 100

  return (
    <div className="space-y-2">
      <div className="relative h-8">
        <div className="absolute inset-x-0 top-3 h-2 rounded-full bg-muted" />
        <div
          className="absolute top-3 h-2 rounded-full bg-primary/30"
          style={{
            left: `${position(lower)}%`,
            width: `${Math.max(position(upper) - position(lower), 1)}%`,
          }}
          aria-hidden="true"
        />
        <div
          className="absolute top-1.5 h-5 w-0.5 bg-foreground"
          style={{ left: `${position(point)}%` }}
          aria-hidden="true"
        />
      </div>
      <div className="flex items-center justify-between font-mono text-xs text-muted-foreground">
        <span>{formatMoney(lower)}</span>
        <span>{formatMoney(point)}</span>
        <span>{formatMoney(upper)}</span>
      </div>
    </div>
  )
}

function RunReport({ run }: { run: BacktestRun }) {
  const report = run.report
  const interval = report?.interval ?? null
  const lookahead = report?.lookahead ?? null

  return (
    <div className="space-y-6">
      <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold">{run.name}</h2>
          <span className="text-sm text-muted-foreground">
            {run.decision_count} decision(s) compared
          </span>
        </div>

        <dl className="grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-muted-foreground">Engine mean net</dt>
            <dd className="font-mono text-lg">
              {report?.mean_engine_net !== null && report?.mean_engine_net !== undefined
                ? formatMoney(report.mean_engine_net)
                : '-'}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Baseline mean net</dt>
            <dd className="font-mono text-lg">
              {report?.mean_baseline_net !== null && report?.mean_baseline_net !== undefined
                ? formatMoney(report.mean_baseline_net)
                : '-'}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Mean difference</dt>
            <dd className="font-mono text-lg">
              {report?.mean_difference !== null && report?.mean_difference !== undefined
                ? formatMoney(report.mean_difference)
                : '-'}
            </dd>
          </div>
        </dl>

        {interval ? (
          <div className="space-y-2">
            <div className="flex items-baseline justify-between">
              <span className="text-sm font-medium">
                Difference per unit, {Math.round(interval.confidence * 100)}% interval
              </span>
              <span className="font-mono text-sm text-muted-foreground">
                {interval.excludes_zero ? 'excludes zero' : 'includes zero'}
              </span>
            </div>
            <IntervalBar
              point={interval.point_estimate}
              lower={interval.lower}
              upper={interval.upper}
            />
            <p className="text-xs text-muted-foreground">
              {interval.method}, {interval.samples} resamples, seed {interval.seed}, n ={' '}
              {interval.n}.
            </p>
          </div>
        ) : (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 text-sm">
            No interval could be computed. There are too few comparable decisions for the
            difference to be summarised with a confidence interval, so only the point estimate
            is shown.
          </div>
        )}

        <div className="flex flex-wrap gap-4 border-t pt-4 text-sm">
          <span>
            <span className="text-muted-foreground">Baseline: </span>
            {report?.baseline_name ?? run.baseline_name}
            {run.baseline_channel ? ` (${run.baseline_channel})` : ''}
          </span>
          {report?.win_rate !== null && report?.win_rate !== undefined && (
            <span>
              <span className="text-muted-foreground">Engine better on: </span>
              {Math.round(report.win_rate * 100)}% of units
            </span>
          )}
        </div>
      </div>

      {lookahead && (
        <div
          className={
            lookahead.has_leak
              ? 'rounded-lg border border-red-200 bg-red-50 p-4 text-red-800'
              : 'rounded-lg border border-green-200 bg-green-50 p-4 text-green-900'
          }
        >
          <div className="flex items-start gap-3">
            {lookahead.has_leak ? (
              <ShieldAlert className="h-5 w-5 flex-shrink-0 mt-0.5" />
            ) : (
              <ShieldCheck className="h-5 w-5 flex-shrink-0 mt-0.5" />
            )}
            <div>
              <p className="font-medium">
                {lookahead.has_leak
                  ? 'This backtest was refused: it used data from the future.'
                  : 'No look-ahead: every source was dated before the decision that used it.'}
              </p>
              {lookahead.findings.length > 0 && (
                <ul className="mt-2 list-disc pl-5 text-sm">
                  {lookahead.findings.map((finding) => (
                    <li key={`${finding.decision_id}:${finding.field}`}>
                      <span className="font-mono">{finding.field}</span>: {finding.detail}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {report?.warnings && report.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">
          <p className="font-medium">Read this before quoting the number</p>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {report.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {report?.skipped && report.skipped.length > 0 && (
        <details className="rounded-lg border bg-card p-4">
          <summary className="cursor-pointer text-sm font-medium">
            {report.skipped.length} decision(s) left out of the comparison
          </summary>
          <ul className="mt-3 space-y-2 text-sm">
            {report.skipped.map((skip) => (
              <li key={skip.decision_id}>
                <span className="font-mono text-xs">{skip.decision_id}</span>: {skip.reason}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

export function BacktestPage() {
  const queryClient = useQueryClient()
  const [orgId, setOrgId] = useState('')
  const [baselineChannel, setBaselineChannel] = useState('LIQUIDATE')
  const [activeRun, setActiveRun] = useState<BacktestRun | null>(null)

  const runsQuery = useQuery({
    queryKey: ['backtests'],
    queryFn: () => listBacktests(),
  })

  const runMutation = useMutation({
    mutationFn: () =>
      createBacktest({
        org_id: orgId,
        name: 'Backtest',
        baseline: 'fixed-channel',
        baseline_channel: baselineChannel,
        samples: 2000,
      }),
    onSuccess: (run) => {
      setActiveRun(run)
      void queryClient.invalidateQueries({ queryKey: ['backtests'] })
    },
  })

  const error = runMutation.error as { response?: { data?: { detail?: unknown } } } | null
  const detail = error?.response?.data?.detail
  const errorMessage =
    typeof detail === 'string'
      ? detail
      : detail && typeof detail === 'object' && 'message' in detail
        ? String((detail as { message: string }).message)
        : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Historical backtest</h1>
        <p className="text-muted-foreground mt-1">
          Replays past decisions using only what was known at the time, and compares the engine
          against the partner&apos;s baseline policy.
        </p>
      </div>

      <div className="rounded-lg border bg-card p-6 shadow-sm">
        <div className="flex flex-wrap items-end gap-4">
          <div className="min-w-[220px] flex-1">
            <label htmlFor="org-id" className="mb-1 block text-xs font-medium text-muted-foreground">
              Organisation id
            </label>
            <input
              id="org-id"
              value={orgId}
              onChange={(event) => setOrgId(event.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
              className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm"
            />
          </div>
          <div>
            <label
              htmlFor="baseline-channel"
              className="mb-1 block text-xs font-medium text-muted-foreground"
            >
              Baseline channel
            </label>
            <select
              id="baseline-channel"
              value={baselineChannel}
              onChange={(event) => setBaselineChannel(event.target.value)}
              className="h-9 rounded-lg border border-input bg-background px-3 text-sm"
            >
              {CHANNELS.map((channel) => (
                <option key={channel} value={channel}>
                  {channel}
                </option>
              ))}
            </select>
          </div>
          <Button
            onClick={() => runMutation.mutate()}
            disabled={!orgId || runMutation.isPending}
          >
            {runMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <FlaskConical className="mr-2 h-4 w-4" />
            )}
            Run backtest
          </Button>
        </div>
        {errorMessage && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}
      </div>

      {activeRun && <RunReport run={activeRun} />}

      {runsQuery.data && runsQuery.data.length > 0 && (
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">Previous runs</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Baseline</th>
                  <th className="py-2 pr-4 font-medium">Decisions</th>
                  <th className="py-2 pr-4 font-medium">Difference</th>
                  <th className="py-2 pr-4 font-medium">Interval</th>
                  <th className="py-2 font-medium">Run</th>
                </tr>
              </thead>
              <tbody>
                {runsQuery.data.map((run) => (
                  <tr key={run.id} className="border-b last:border-0">
                    <td className="py-2 pr-4">{run.name}</td>
                    <td className="py-2 pr-4">
                      {run.baseline_name}
                      {run.baseline_channel ? ` (${run.baseline_channel})` : ''}
                    </td>
                    <td className="py-2 pr-4 font-mono">{run.decision_count}</td>
                    <td className="py-2 pr-4 font-mono">
                      {run.mean_difference === null ? '-' : formatMoney(run.mean_difference)}
                    </td>
                    <td className="py-2 pr-4 font-mono">
                      {run.ci_lower === null || run.ci_upper === null
                        ? '-'
                        : `${formatMoney(run.ci_lower)} to ${formatMoney(run.ci_upper)}`}
                    </td>
                    <td className="py-2">
                      <button
                        onClick={() => setActiveRun(run)}
                        className="text-primary underline-offset-2 hover:underline"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
