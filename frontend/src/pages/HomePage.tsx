import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  CircleDashed,
  Database,
  Gauge,
  Loader2,
  Package,
  Server,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { getHealth } from '@/api/health'
import { getNorthStar } from '@/api/decision'
import { formatMoney } from '@/types/decision'
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Skeleton,
} from '@/components/ui'

/**
 * The dashboard.
 *
 * The north star is the number the whole product exists to move: the value
 * recovered from a return, against what the partner would have recovered
 * without it. Everything else on the page is either the state of the
 * system or the work waiting to be done.
 */
export function HomePage() {
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000,
  })

  const northStarQuery = useQuery({
    queryKey: ['analytics', 'north-star'],
    queryFn: getNorthStar,
  })

  const northStar = northStarQuery.data
  const synthetic = northStar?.synthetic
  const real = northStar?.real

  // The real numbers are the ones that count. The synthetic ones are shown
  // only when there is nothing else, and always labelled.
  const headline = real && real.returns_count > 0 ? real : synthetic
  const isSynthetic = !(real && real.returns_count > 0)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">The dashboard</h1>
        <p className="mt-1 text-muted-foreground">
          What the engine recovered, and what is waiting to be done.
        </p>
      </div>

      {/* The north star. */}
      <section aria-labelledby="north-star-heading" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="north-star-heading" className="text-lg font-semibold">
            The north star
          </h2>
          {isSynthetic && (
            <Badge variant="yellow">
              <Sparkles className="size-3" aria-hidden="true" />
              Synthetic data
            </Badge>
          )}
        </div>

        {northStarQuery.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-3">
            {[0, 1, 2].map((index) => (
              <Skeleton key={index} className="h-28" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardHeader className="gap-1">
                <CardTitle className="text-sm font-normal text-muted-foreground">
                  Net recovered per return
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-mono text-3xl font-semibold" data-testid="net-recovered">
                  {formatMoney(headline?.net_recovered_per_return ?? 0)}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {headline?.returns_count ?? 0} returns
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="gap-1">
                <CardTitle className="text-sm font-normal text-muted-foreground">
                  The baseline
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-mono text-3xl font-semibold">
                  {formatMoney(headline?.baseline_per_return ?? 0)}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  What {northStar?.baseline_channel ?? 'the baseline'} would have given
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="gap-1">
                <CardTitle className="text-sm font-normal text-muted-foreground">
                  Above the baseline
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p
                  className={cn(
                    'font-mono text-3xl font-semibold',
                    (headline?.above_baseline_per_return ?? 0) >= 0
                      ? 'text-lime'
                      : 'text-destructive'
                  )}
                  data-testid="above-baseline"
                >
                  {formatMoney(headline?.above_baseline_per_return ?? 0)}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">per return</p>
              </CardContent>
            </Card>
          </div>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* The work waiting. */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>The work</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <QuickAction
              href="/intake/new"
              icon={<Package className="size-4" />}
              title="Log a return"
              description="A unit that has come back and nobody has written down yet."
            />
            <QuickAction
              href="/units"
              icon={<Gauge className="size-4" />}
              title="Inspect and decide"
              description="The units that are waiting for an inspection or a decision."
            />
            <QuickAction
              href="/analytics"
              icon={<TrendingUp className="size-4" />}
              title="See how the engine is doing"
              description="What it recovered, and how often it was wrong."
            />
          </CardContent>
        </Card>

        {/* The state of the system. */}
        <Card>
          <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
            <CardTitle>The system</CardTitle>
            {healthQuery.data && (
              <Badge variant={healthQuery.data.status === 'healthy' ? 'lime' : 'yellow'}>
                {healthQuery.data.status}
              </Badge>
            )}
          </CardHeader>
          <CardContent>
            {healthQuery.isLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                Checking...
              </div>
            ) : healthQuery.isError ? (
              <div className="flex items-start gap-2 text-sm text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                The service could not be reached.
              </div>
            ) : (
              <ul className="space-y-3">
                <ServiceRow
                  icon={<Server className="size-4" />}
                  name="The API"
                  // The API answered, so it is up. The overall status is
                  // about the whole system, which is a different thing.
                  ok
                  detail={`${healthQuery.data?.environment ?? 'unknown'}, version ${healthQuery.data?.version ?? '—'}`}
                />
                <ServiceRow
                  icon={<Database className="size-4" />}
                  name="The database"
                  ok={healthQuery.data?.checks.database === 'ok'}
                  detail={healthQuery.data?.checks.database === 'ok' ? 'Connected' : 'Not reachable'}
                />
                <ServiceRow
                  icon={<CircleDashed className="size-4" />}
                  name="The queue"
                  ok={healthQuery.data?.checks.redis === 'ok'}
                  detail={healthQuery.data?.checks.redis === 'ok' ? 'Connected' : 'Not reachable'}
                />
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function QuickAction({
  href,
  icon,
  title,
  description,
}: {
  href: string
  icon: ReactNode
  title: string
  description: string
}) {
  return (
    <Link
      to={href}
      className="group flex items-start gap-3 rounded-2xl border bg-card p-4 transition-colors hover:border-outline hover:bg-accent/40"
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-1.5 text-sm font-medium">
          {title}
          <ArrowRight
            className="size-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5"
            aria-hidden="true"
          />
        </span>
        <span className="mt-0.5 block text-sm text-muted-foreground">{description}</span>
      </span>
    </Link>
  )
}

function ServiceRow({
  icon,
  name,
  ok,
  detail,
}: {
  icon: ReactNode
  name: string
  ok: boolean
  detail: string
}) {
  return (
    <li className="flex items-center gap-3">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium">{name}</span>
        <span className="block truncate text-xs text-muted-foreground">{detail}</span>
      </span>
      {ok ? (
        <CheckCircle2 className="size-4 shrink-0 text-lime" aria-label="Up" />
      ) : (
        <AlertCircle className="size-4 shrink-0 text-destructive" aria-label="Down" />
      )}
    </li>
  )
}
