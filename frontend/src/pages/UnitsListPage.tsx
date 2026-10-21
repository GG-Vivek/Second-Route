import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Loader2, Plus, Search } from 'lucide-react'
import { format } from 'date-fns'
import { cn } from '@/utils/cn'
import {
  Badge,
  Button,
  ButtonLink,
  EmptyState,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui'
import {
  listUnits,
  type Unit,
  type UnitStatus,
  UNIT_STATUSES,
} from '@/api/intake'

/** The colour of each status. */
const STATUS_TONE: Record<UnitStatus, 'default' | 'secondary' | 'outline' | 'lime' | 'teal' | 'purple' | 'orange'> = {
  received: 'secondary',
  inspected: 'orange',
  decided: 'purple',
  dispatched: 'teal',
  sold: 'lime',
  recycled: 'outline',
  donated: 'default',
}

export function UnitsListPage() {
  const [units, setUnits] = useState<Unit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<UnitStatus | 'all'>('all')
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const pageSize = 20

  const fetchUnits = useCallback(async () => {
    try {
      setLoading(true)
      const data = await listUnits({
        status: statusFilter === 'all' ? undefined : statusFilter,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      })
      if (page === 1) {
        setUnits(data)
      } else {
        setUnits((previous) => [...previous, ...data])
      }
      setHasMore(data.length === pageSize)
      setError(null)
    } catch {
      setError('The units could not be loaded.')
    } finally {
      setLoading(false)
    }
  }, [statusFilter, page, pageSize])

  useEffect(() => {
    void fetchUnits()
  }, [fetchUnits])

  const filteredUnits = useMemo(() => {
    if (!search) return units
    const needle = search.toLowerCase()
    return units.filter(
      (unit) =>
        unit.id.toLowerCase().includes(needle) ||
        (unit.serial?.toLowerCase().includes(needle) ?? false) ||
        unit.return_reason_code.toLowerCase().includes(needle) ||
        unit.order_channel.toLowerCase().includes(needle)
    )
  }, [units, search])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Units</h1>
          <p className="mt-1 text-muted-foreground">
            Every returned unit, its inspection and its decision.
          </p>
        </div>
        <ButtonLink href="/intake/new">
          <Plus className="size-4" aria-hidden="true" />
          New unit
        </ButtonLink>
      </div>

      {/* The filters. */}
      <div className="flex flex-wrap items-center gap-3 rounded-4xl border bg-card p-4 shadow-md ring-1 ring-foreground/5 dark:ring-foreground/10">
        <div className="relative min-w-[16rem] flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
            placeholder="Search by serial, reason or channel"
            aria-label="Search the units"
            className="w-full rounded-xl border border-input bg-background py-2 pl-9 pr-3 text-sm transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/30 focus-visible:outline-none"
          />
        </div>

        <div
          className="inline-flex items-center gap-1 rounded-full bg-muted p-1"
          role="group"
          aria-label="Filter by status"
        >
          {(['all', ...UNIT_STATUSES.map((status) => status.value)] as const).map((status) => {
            const active = statusFilter === status
            const label =
              status === 'all'
                ? 'All'
                : (UNIT_STATUSES.find((entry) => entry.value === status)?.label ?? status)
            return (
              <button
                key={status}
                type="button"
                aria-pressed={active}
                onClick={() => {
                  setStatusFilter(status as UnitStatus | 'all')
                  setPage(1)
                }}
                className={cn(
                  'rounded-full px-3 py-1 text-sm font-medium transition-colors',
                  active
                    ? 'bg-background text-foreground shadow-xs dark:bg-input/30'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {/* The list. */}
      {loading && units.length === 0 ? (
        <div className="flex items-center justify-center rounded-4xl border p-16">
          <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden="true" />
        </div>
      ) : error ? (
        <EmptyState
          title="The units could not be loaded"
          description={error}
          action={<Button onClick={() => void fetchUnits()}>Try again</Button>}
        />
      ) : filteredUnits.length === 0 ? (
        <EmptyState
          title="No units yet"
          description={
            search || statusFilter !== 'all'
              ? 'Nothing matches that search. Try a different one.'
              : 'Log a return and it will appear here.'
          }
          action={
            <ButtonLink href="/intake/new">
              <Plus className="size-4" aria-hidden="true" />
              Log a return
            </ButtonLink>
          }
        />
      ) : (
        <div className="overflow-hidden rounded-4xl border bg-card shadow-md ring-1 ring-foreground/5 dark:ring-foreground/10">
          <TableContainer>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Unit</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Channel</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Received</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUnits.map((unit) => (
                  <TableRow key={unit.id}>
                    <TableCell className="font-mono text-xs">
                      {unit.serial ?? unit.id.slice(0, 8)}
                    </TableCell>
                    <TableCell>
                      {unit.sku ? `${unit.sku.family} ${unit.sku.model_name}` : 'Unknown'}
                    </TableCell>
                    <TableCell className="capitalize">
                      {unit.return_reason_code.replace(/_/g, ' ')}
                    </TableCell>
                    <TableCell className="capitalize">{unit.order_channel}</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_TONE[unit.status] ?? 'secondary'}>
                        {UNIT_STATUSES.find((entry) => entry.value === unit.status)?.label ??
                          unit.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {format(new Date(unit.received_at), 'PP')}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link
                        to={`/units/${unit.id}`}
                        className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                      >
                        Open
                        <ArrowRight className="size-3.5" aria-hidden="true" />
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {hasMore && (
            <div className="border-t p-3">
              <Button
                variant="ghost"
                className="w-full"
                onClick={() => setPage((current) => current + 1)}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                    Loading...
                  </>
                ) : (
                  'Load more'
                )}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
