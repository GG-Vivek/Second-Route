import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FlaskConical, Loader2, ShieldAlert, ShieldCheck } from 'lucide-react'
import { format } from 'date-fns'
import { Button, Callout, Card, CardContent, CardHeader, CardTitle, Field, inputClass } from '@/components/ui'
import { createBacktest, listBacktests, type BacktestRun } from '@/api/backtest'
import { formatMoney } from '@/types/decision'

/** The channels the engine can recommend. */
const CHANNELS = ['LIQUIDATE', 'RESELL', 'RECYCLE', 'PARTS_HARVEST', 'DONATE']

/**
 * The interval of a backtest.
 *
 * The band is the interval and the mark is the point estimate. The
 * interval is what decides whether the number can be quoted: a difference
 * whose interval includes zero is not a difference.
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
          className="absolute top-1.5 h-5 w-px bg-foreground"
          style={{ left: `${position(point)}%` }}
          aria-hidden="true"
        />
      </div>
      <div className="flex items-center justify-between font-mono text-xs text-muted-foreground">
        <span>{formatMoney(lower)}</span>
        <span className="text-foreground">{formatMoney(point)}</span>
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
      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
          <CardTitle>{run.name}</CardTitle>
          <span className="text-sm text-muted-foreground">
            {run.decision_count} decision(s) compared
          </span>
        </CardHeader>
        <CardContent className="space-y-6">
          <dl className="grid gap-4 sm:grid-cols-3">
            <div>
              <dt className="text-xs text-muted-foreground">Engine mean net</dt>
              <dd className="font-mono text-2xl font-semibold">
                {report?.mean_engine_net !== null && report?.mean_engine_net !== undefined
                  ? formatMoney(report.mean_engine_net)
                  : '-'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Baseline mean net</dt>
              <dd className="font-mono text-2xl font-semibold">
                {report?.mean_baseline_net !== null && report?.mean_baseline_net !== undefined
                  ? formatMoney(report.mean_baseline_net)
                  : '-'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Mean difference</dt>
              <dd className="font-mono text-2xl font-semibold text-lime">
                {report?.mean_difference !== null && report?.mean_difference !== undefined
                  ? formatMoney(report.mean_difference)
                  : '-'}
              </dd>
            </div>
          </dl>

          {interval ? (
            <div className="space-y-2">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
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
            <Callout tone="warning" title="No interval could be computed">
              <p>
                There are too few comparable decisions for the difference to be summarised with
                a confidence interval, so only the point estimate is shown.
              </p>
            </Callout>
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
        </CardContent>
      </Card>

      {lookahead && (
        <Callout
          tone={lookahead.has_leak ? 'caution' : 'tip'}
          title={
            lookahead.has_leak
              ? 'This backtest was refused: it used data from the future.'
              : 'No look-ahead: every source was dated before the decision that used it.'
          }
          icon={
            lookahead.has_leak ? (
              <ShieldAlert className="size-4" aria-hidden="true" />
            ) : (
              <ShieldCheck className="size-4" aria-hidden="true" />
            )
          }
        >
          {lookahead.findings.length > 0 && (
            <ul className="mt-2 list-disc pl-5 space-y-1">
              {lookahead.findings.map((finding) => (
                <li key={`${finding.decision_id}:${finding.field}`}>
                  <span className="font-mono">{finding.field}</span>: {finding.detail}
                </li>
              ))}
            </ul>
          )}
        </Callout>
      )}

      {report?.warnings && report.warnings.length > 0 && (
        <Callout tone="warning" title="Read this before quoting the number">
          <ul className="mt-2 list-disc pl-5 space-y-1">
            {report.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </Callout>
      )}

      {report?.skipped && report.skipped.length > 0 && (
        <details className="rounded-2xl border bg-card p-4">
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
        <p className="mt-1 text-muted-foreground">
          Replays past decisions using only what was known at the time, and compares the engine
          against the partner&apos;s baseline policy.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-4 pt-6">
          <div className="min-w-[14rem] flex-1">
            <Field label="Organisation id">
              {({ id }) => (
                <input
                  id={id}
                  value={orgId}
                  onChange={(event) => setOrgId(event.target.value)}
                  placeholder="00000000-0000-0000-0000-000000000000"
                  className={inputClass}
                />
              )}
            </Field>
          </div>
          <div className="min-w-[12rem]">
            <Field label="Baseline channel">
              {({ id }) => (
                <select
                  id={id}
                  value={baselineChannel}
                  onChange={(event) => setBaselineChannel(event.target.value)}
                  className={inputClass}
                >
                  {CHANNELS.map((channel) => (
                    <option key={channel} value={channel}>
                      {channel}
                    </option>
                  ))}
                </select>
              )}
            </Field>
          </div>
          <Button onClick={() => runMutation.mutate()} disabled={!orgId || runMutation.isPending}>
            {runMutation.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                Running...
              </>
            ) : (
              <>
                <FlaskConical className="size-4" aria-hidden="true" />
                Run backtest
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {errorMessage && (
        <Callout tone="caution" title="The backtest was refused">
          <p>{errorMessage}</p>
        </Callout>
      )}

      {activeRun && <RunReport run={activeRun} />}

      {runsQuery.data && runsQuery.data.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Previous runs</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-border">
              {runsQuery.data.map((run) => (
                <li key={run.id} className="flex flex-wrap items-center gap-4 py-3">
                  <span className="font-medium">{run.name}</span>
                  <span className="text-sm text-muted-foreground">
                    {run.baseline_name}
                    {run.baseline_channel ? ` (${run.baseline_channel})` : ''}
                  </span>
                  <span className="font-mono text-sm text-muted-foreground">
                    {run.decision_count} decisions
                  </span>
                  <span className="font-mono text-sm">
                    {run.mean_difference === null
                      ? '-'
                      : formatMoney(run.mean_difference)}
                  </span>
                  <span className="font-mono text-sm text-muted-foreground">
                    {run.ci_lower === null || run.ci_upper === null
                      ? '-'
                      : `${formatMoney(run.ci_lower)} to ${formatMoney(run.ci_upper)}`}
                  </span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {format(new Date(run.created_at), 'PP')}
                  </span>
                  <button
                    onClick={() => setActiveRun(run)}
                    className="ml-auto text-sm font-medium text-primary hover:underline"
                  >
                    View
                  </button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
