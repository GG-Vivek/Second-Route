import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  Camera,
  ClipboardCheck,
  Loader2,
  Play,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react'
import { format } from 'date-fns'
import { cn } from '@/utils/cn'
import {
  Badge,
  Button,
  ButtonLink,
  Callout,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui'
import {
  getUnit,
  type UnitDetail,
  type UnitStatus,
  type Photo,
  UNIT_STATUSES,
  gradeColor,
  lockColor,
} from '@/api/intake'
import { listUnitDecisions } from '@/api/decision'

const STATUS_TONE: Record<
  UnitStatus,
  'default' | 'secondary' | 'outline' | 'lime' | 'teal' | 'purple' | 'orange'
> = {
  received: 'secondary',
  inspected: 'orange',
  decided: 'purple',
  dispatched: 'teal',
  sold: 'lime',
  recycled: 'outline',
  donated: 'default',
}

export function UnitDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [unit, setUnit] = useState<UnitDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchUnit() {
      if (!id) return
      try {
        setLoading(true)
        const data = await getUnit(id)
        setUnit(data)
        setError(null)
      } catch (fetchError: unknown) {
        const apiError = fetchError as { response?: { status: number } }
        setError(
          apiError.response?.status === 404
            ? 'That unit does not exist.'
            : 'The unit could not be loaded.'
        )
      } finally {
        setLoading(false)
      }
    }
    void fetchUnit()
  }, [id])

  const decisionsQuery = useQuery({
    queryKey: ['unit-decisions', id],
    queryFn: () => listUnitDecisions(id ?? ''),
    enabled: Boolean(id),
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden="true" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl py-12">
        <Callout tone="caution" title="The unit could not be opened">
          <p>{error}</p>
        </Callout>
        <Button variant="outline" className="mt-4" onClick={() => navigate(-1)}>
          Go back
        </Button>
      </div>
    )
  }

  if (!unit) return null

  const inspections = [...unit.inspections].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

  return (
    <div className="space-y-6">
      {/* The header. */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(-1)}
            aria-label="Go back"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
          </Button>
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">
                {unit.sku ? `${unit.sku.family} ${unit.sku.model_name}` : 'Unknown model'}
              </h1>
              <Badge variant={STATUS_TONE[unit.status] ?? 'secondary'}>
                {UNIT_STATUSES.find((entry) => entry.value === unit.status)?.label ?? unit.status}
              </Badge>
            </div>
            <p className="mt-1 font-mono text-sm text-muted-foreground">
              {unit.serial ?? unit.id}
              {unit.sku ? ` - ${unit.sku.year}, ${unit.sku.storage_gb}GB` : ''}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <ButtonLink href={`/units/${unit.id}/inspection/new`} variant="outline">
            <ClipboardCheck className="size-4" aria-hidden="true" />
            Inspect
          </ButtonLink>
          <ButtonLink href={`/units/${unit.id}/decision`}>
            <Play className="size-4" aria-hidden="true" />
            Decide
          </ButtonLink>
        </div>
      </div>

      {/* The facts. */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Fact label="Return reason" value={unit.return_reason_code.replace(/_/g, ' ')} />
        <Fact label="Order channel" value={unit.order_channel} />
        <Fact label="Received" value={format(new Date(unit.received_at), 'PPp')} />
        <Fact
          label="Model source"
          value={unit.sku ? unit.sku.source : 'Unknown'}
          hint={unit.sku ? `as of ${unit.sku.as_of}` : undefined}
        />
      </div>

      {unit.notes && (
        <Card>
          <CardHeader>
            <CardTitle>Notes from the intake</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">{unit.notes}</p>
          </CardContent>
        </Card>
      )}

      {/* The tabs. */}
      <Tabs defaultValue="inspection">
        <TabsList>
          <TabsTrigger value="inspection">Inspection</TabsTrigger>
          <TabsTrigger value="photos">Photos ({unit.photos.length})</TabsTrigger>
          <TabsTrigger value="decisions">
            Decisions ({decisionsQuery.data?.total ?? 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="inspection">
          {inspections.length === 0 ? (
            <EmptyState
              icon={<ClipboardCheck className="size-6" />}
              title="No inspection yet"
              description="Inspect the unit so that the engine has something to work from."
              action={
                <ButtonLink href={`/units/${unit.id}/inspection/new`}>
                  Start the inspection
                </ButtonLink>
              }
            />
          ) : (
            <div className="space-y-3">
              {inspections.map((inspection) => (
                <Card key={inspection.id}>
                  <CardHeader className="flex-row items-center justify-between gap-3">
                    <CardTitle>Inspection</CardTitle>
                    <span className="font-mono text-xs text-muted-foreground">
                      {format(new Date(inspection.created_at), 'PPp')}
                    </span>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex flex-wrap gap-2">
                      <Badge className={cn(gradeColor(inspection.cosmetic_grade))}>
                        Grade {inspection.cosmetic_grade}
                      </Badge>
                      <Badge className={cn(lockColor(inspection.activation_lock))}>
                        {inspection.activation_lock === 'none'
                          ? 'No lock'
                          : inspection.activation_lock === 'present'
                            ? 'Locked'
                            : 'Unknown'}
                      </Badge>
                      {inspection.battery_health_pct && (
                        <Badge variant="secondary">
                          {inspection.battery_health_pct}% battery
                        </Badge>
                      )}
                      {inspection.battery_cycles && (
                        <Badge variant="secondary">
                          {inspection.battery_cycles} cycles
                        </Badge>
                      )}
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <FactList
                        title="Functional tests"
                        entries={Object.entries(inspection.functional_tests_json)}
                      />
                      <FactList
                        title="Accessories"
                        entries={Object.entries(inspection.accessories_json)}
                      />
                    </div>

                    {inspection.notes && (
                      <p className="whitespace-pre-wrap rounded-2xl bg-muted p-4 text-sm text-muted-foreground">
                        {inspection.notes}
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="photos">
          {unit.photos.length === 0 ? (
            <EmptyState
              icon={<Camera className="size-6" />}
              title="No photographs"
              description="Photographs are taken against the inspection and stored with it."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {unit.photos.map((photo) => (
                <PhotoTile key={photo.id} photo={photo} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="decisions">
          {decisionsQuery.isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden="true" />
            </div>
          ) : (decisionsQuery.data?.items.length ?? 0) === 0 ? (
            <EmptyState
              icon={<Play className="size-6" />}
              title="No decision yet"
              description="Run the engine to get a disposition recommendation for this unit."
              action={<ButtonLink href={`/units/${unit.id}/decision`}>Run the decision</ButtonLink>}
            />
          ) : (
            <ul className="space-y-2">
              {decisionsQuery.data?.items.map((summary) => (
                <li key={summary.id}>
                  <Link
                    to={`/units/${unit.id}/decision`}
                    className="flex items-center justify-between gap-4 rounded-2xl border bg-card p-4 transition-colors hover:bg-accent/40"
                  >
                    <span className="flex items-center gap-3">
                      <span className="font-medium">{summary.recommended_channel}</span>
                      {summary.fallback_used && (
                        <Badge variant="yellow">
                          <ShieldAlert className="size-3" aria-hidden="true" />
                          Safe default
                        </Badge>
                      )}
                    </span>
                    <span className="flex items-center gap-4 font-mono text-xs text-muted-foreground">
                      {(summary.confidence * 100).toFixed(1)}% - {summary.risk_profile}
                      <ShieldCheck className="size-3.5" aria-hidden="true" />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

function Fact({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <div className="rounded-4xl border bg-card p-4 shadow-md ring-1 ring-foreground/5 dark:ring-foreground/10">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-sm font-medium capitalize">{value}</p>
      {hint && <p className="mt-0.5 font-mono text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

function FactList({
  title,
  entries,
}: {
  title: string
  entries: [string, boolean][]
}) {
  if (entries.length === 0) {
    return (
      <div>
        <p className="mb-2 text-xs font-medium text-muted-foreground">{title}</p>
        <p className="text-sm text-muted-foreground">Nothing recorded.</p>
      </div>
    )
  }

  return (
    <div>
      <p className="mb-2 text-xs font-medium text-muted-foreground">{title}</p>
      <ul className="flex flex-wrap gap-2">
        {entries.map(([name, passed]) => (
          <li key={name}>
            <Badge variant={passed ? 'lime' : 'destructive'}>
              {name.replace(/_/g, ' ')}
              <span className="opacity-70">{passed ? 'pass' : 'fail'}</span>
            </Badge>
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * One photograph.
 *
 * The photograph is served from the upload directory. When it is not
 * there, the tile says so rather than showing a broken image.
 */
function PhotoTile({ photo }: { photo: Photo }) {
  const [failed, setFailed] = useState(false)

  return (
    <figure className="overflow-hidden rounded-2xl border bg-card">
      <div className="relative aspect-square bg-muted">
        {!failed ? (
          <img
            src={photo.storage_path}
            alt={`Photograph taken ${format(new Date(photo.created_at), 'PPp')}`}
            className="size-full object-cover"
            onError={() => setFailed(true)}
            loading="lazy"
          />
        ) : (
          <div className="flex size-full flex-col items-center justify-center gap-2 text-muted-foreground">
            <Camera className="size-6" aria-hidden="true" />
            <span className="text-xs">The file is not there</span>
          </div>
        )}
        <span className="absolute right-2 top-2">
          <Badge variant={photo.exif_stripped ? 'lime' : 'yellow'}>
            {photo.exif_stripped ? 'EXIF stripped' : 'EXIF present'}
          </Badge>
        </span>
      </div>
      <figcaption className="px-3 py-2 font-mono text-xs text-muted-foreground">
        {format(new Date(photo.created_at), 'PPp')}
      </figcaption>
    </figure>
  )
}
