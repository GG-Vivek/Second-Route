import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { AlertCircle, CheckCircle2, Clock, Database, FlaskConical, Server, TriangleAlert } from 'lucide-react'
import { getHealth, getSourceHealth, type DependencyState } from '@/api/health'
import {
  Badge,
  Callout,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
} from '@/components/ui'
import { MEANING } from '@/theme/meaning'

/**
 * The health of the system.
 *
 * Two things are on this page: whether the service is up, and whether the
 * data behind the decisions is fresh. The second one matters more, because
 * a stale source does not stop the engine, it only quietly lowers the
 * confidence of everything the engine says.
 */
export function HealthPage() {
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000,
  })

  const sourcesQuery = useQuery({
    queryKey: ['sources', 'health'],
    queryFn: getSourceHealth,
  })

  const health = healthQuery.data
  const sourceHealth = sourcesQuery.data
  const sources = sourceHealth?.sources ?? []

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Health</h1>
        <p className="mt-1 text-muted-foreground">
          Whether the service is up, and whether the data behind the decisions is fresh.
        </p>
      </div>

      {/* The service. */}
      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
          <CardTitle>The service</CardTitle>
          {healthQuery.isLoading ? (
            <Skeleton className="h-5 w-20" />
          ) : healthQuery.isError ? (
            <Badge variant="destructive">Unreachable</Badge>
          ) : (
            <Badge variant={health?.status === 'healthy' ? 'lime' : 'yellow'}>
              {health?.status === 'healthy' ? (
                <CheckCircle2 className="size-3" aria-hidden="true" />
              ) : (
                <AlertCircle className="size-3" aria-hidden="true" />
              )}
              {health?.status ?? 'unknown'}
            </Badge>
          )}
        </CardHeader>
        <CardContent>
          {healthQuery.isLoading ? (
            <Skeleton className="h-16" />
          ) : healthQuery.isError ? (
            <p className="text-sm text-destructive">
              The service could not be reached. Check that the API is running.
            </p>
          ) : (
            <>
              <ul className="grid gap-4 sm:grid-cols-3">
                <Service
                  icon={<Server className="size-4" />}
                  name="The API"
                  ok={health?.status === 'healthy'}
                  detail={`${health?.environment ?? 'unknown'}, version ${health?.version ?? '—'}`}
                />
                <Service
                  icon={<Database className="size-4" />}
                  name="The database"
                  state={health?.checks.database}
                  detail={describe(health?.checks.database, 'Not reachable')}
                />
                <Service
                  icon={<Clock className="size-4" />}
                  name="The cache"
                  state={health?.checks.redis}
                  detail={describe(health?.checks.redis, 'Not reachable')}
                />
              </ul>
            </>
          )}
        </CardContent>
      </Card>

      {/* The sources. */}
      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
          <CardTitle>The data sources</CardTitle>
          {sourceHealth && sourceHealth.summary.total > 0 && (
            <span className="flex flex-wrap items-center gap-2 text-xs">
              <Badge variant={MEANING.recovered}>{sourceHealth.summary.fresh} fresh</Badge>
              {sourceHealth.summary.stale > 0 && (
                <Badge variant={MEANING.caution}>{sourceHealth.summary.stale} stale</Badge>
              )}
              {sourceHealth.summary.missing > 0 && (
                <Badge variant={MEANING.missing}>{sourceHealth.summary.missing} missing</Badge>
              )}
              {sourceHealth.summary.errors > 0 && (
                <Badge variant="destructive">{sourceHealth.summary.errors} errors</Badge>
              )}
            </span>
          )}
        </CardHeader>
        <CardContent>
          {sourcesQuery.isLoading ? (
            <Skeleton className="h-32" />
          ) : sourcesQuery.isError ? (
            <Callout tone="caution" title="The data sources could not be loaded">
              <p>
                The engine did not answer. No source is reported, which is not the same as no
                source having spoken.
              </p>
            </Callout>
          ) : sources.length === 0 ? (
            <EmptyState
              title="No sources have reported yet"
              description="A source appears here the first time it says something."
            />
          ) : (
            <ul className="divide-y divide-border">
              {sources.map((source) => (
                <li key={`${source.kind}:${source.source}`} className="flex flex-wrap items-center gap-3 py-3">
                  <span className="w-32 shrink-0 truncate font-mono text-sm">{source.source}</span>
                  <Badge variant="secondary">{source.kind}</Badge>
                  {source.is_synthetic && (
                    <Badge variant="yellow">
                      <FlaskConical className="size-3" aria-hidden="true" />
                      Synthetic
                    </Badge>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {source.last_update
                      ? `last spoke ${formatDistanceToNow(new Date(source.last_update), { addSuffix: true })}`
                      : 'has never spoken'}
                  </span>
                  {source.error_count > 0 && (
                    <span className="text-xs text-destructive">
                      {source.error_count} error(s)
                    </span>
                  )}
                  <span className="ml-auto">
                    <SourceBadge status={source.status} />
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function Service({
  icon,
  name,
  ok,
  state,
  detail,
}: {
  icon: ReactNode
  name: string
  ok?: boolean
  state?: DependencyState
  detail: string
}) {
  const up = state ? state === 'ok' : Boolean(ok)
  const unused = state === 'not_configured'

  return (
    <li className="flex items-start gap-3">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium">{name}</span>
        <span className="block truncate text-xs text-muted-foreground">{detail}</span>
      </span>
      {unused ? (
        <span
          className="size-4 shrink-0 rounded-full border border-dashed border-outline"
          aria-label="Not in use"
        />
      ) : up ? (
        <CheckCircle2 className="size-4 shrink-0 text-lime" aria-label="Up" />
      ) : (
        <AlertCircle className="size-4 shrink-0 text-destructive" aria-label="Down" />
      )}
    </li>
  )
}

/** The sentence that says what the state of a dependency is. */
function describe(state: DependencyState | undefined, down: string): string {
  if (state === 'ok') return 'Connected'
  if (state === 'not_configured') return 'Not in use'
  return down
}

/**
 * The condition of one source, drawn in the hue that carries it (ADR-008).
 *
 * Fresh is the state the system wants to be in, so it keeps the brand hue.
 * Stale is a caution and missing is a failure — neither of them is synthetic
 * data, which is what the yellow this page used to draw them in means.
 */
export function SourceBadge({ status }: { status: 'fresh' | 'stale' | 'missing' }) {
  if (status === 'fresh') {
    return (
      <Badge variant={MEANING.recovered}>
        <CheckCircle2 className="size-3" aria-hidden="true" />
        Fresh
      </Badge>
    )
  }
  if (status === 'stale') {
    return (
      <Badge variant={MEANING.caution}>
        <TriangleAlert className="size-3" aria-hidden="true" />
        Stale
      </Badge>
    )
  }
  return (
    <Badge variant={MEANING.missing}>
      <AlertCircle className="size-3" aria-hidden="true" />
      Missing
    </Badge>
  )
}
