import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, Search, Filter, ChevronDown, ChevronUp } from 'lucide-react'
import { format } from 'date-fns'
import { cn } from '@/utils/cn'
import { listUnits, type Unit, type UnitStatus, UNIT_STATUSES } from '@/api/intake'

export function UnitsListPage() {
  const [units, setUnits] = useState<Unit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<UnitStatus | 'all'>('all')
  const [showFilters, setShowFilters] = useState(false)
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
        setUnits((prev) => [...prev, ...data])
      }
      setHasMore(data.length === pageSize)
      setError(null)
    } catch (err) {
      setError('Failed to load units')
    } finally {
      setLoading(false)
    }
  }, [statusFilter, page, pageSize])

  useEffect(() => {
    fetchUnits()
  }, [fetchUnits])

  const statusColor = (status: UnitStatus) => {
    switch (status) {
      case 'received':
        return 'bg-blue-100 text-blue-800'
      case 'inspected':
        return 'bg-yellow-100 text-yellow-800'
      case 'decided':
        return 'bg-purple-100 text-purple-800'
      case 'dispatched':
        return 'bg-indigo-100 text-indigo-800'
      case 'sold':
        return 'bg-green-100 text-green-800'
      case 'recycled':
        return 'bg-gray-100 text-gray-800'
      case 'donated':
        return 'bg-teal-100 text-teal-800'
      default:
        return 'bg-muted text-muted-foreground'
    }
  }

  const filteredUnits = units.filter((unit) => {
    if (!search) return true
    const searchLower = search.toLowerCase()
    return (
      unit.id.toLowerCase().includes(searchLower) ||
      (unit.serial?.toLowerCase().includes(searchLower) ?? false) ||
      unit.return_reason_code.toLowerCase().includes(searchLower) ||
      unit.order_channel.toLowerCase().includes(searchLower)
    )
  })

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Units</h1>
          <p className="text-muted-foreground">Browse and manage returned units</p>
        </div>
        <Link
          to="/intake/new"
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4 rotate-180" />
          New Unit
        </Link>
      </div>

      {/* Search & Filters */}
      <div className="rounded-lg border bg-card p-4 shadow-sm space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Search by ID, serial, reason, channel..."
            className="w-full pl-10 pr-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'px-3 py-2 border rounded-lg text-sm font-medium flex items-center gap-2 transition-colors',
              showFilters ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'
            )}
          >
            <Filter className="h-4 w-4" />
            Filters
            {showFilters ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>

        {showFilters && (
          <div className="space-y-3 pt-2 border-t">
            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value as UnitStatus | 'all')
                  setPage(1)
                }}
                className="w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              >
                <option value="all">All Statuses</option>
                {UNIT_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Units Table */}
      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        {loading && units.length === 0 ? (
          <div className="p-12 text-center">
            <Loader2 className="h-8 w-8 text-primary animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground">Loading units...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center text-red-600">
            <p>Failed to load units</p>
            <button onClick={fetchUnits} className="mt-2 px-4 py-2 border rounded-lg hover:bg-accent transition-colors">
              Retry
            </button>
          </div>
        ) : filteredUnits.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            <p className="text-lg font-medium mb-2">No units found</p>
            <p className="text-sm">Try adjusting your search or filters</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">ID</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Serial</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">SKU</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Reason</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Channel</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Received</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredUnits.map((unit) => (
                    <tr key={unit.id} className="hover:bg-muted/50">
                      <td className="px-4 py-3 text-sm font-mono text-muted-foreground">
                        {unit.id.slice(0, 8)}...
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {unit.serial ? (
                          <span className="font-mono">{unit.serial}</span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm max-w-xs truncate">
                        {unit.sku ? `${unit.sku.family} ${unit.sku.model_name}` : 'Unknown'}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {unit.return_reason_code.replace(/_/g, ' ').replace(/\b\w/g, (letter: string) => letter.toUpperCase())}
                      </td>
                      <td className="px-4 py-3 text-sm">{unit.order_channel}</td>
                      <td className="px-4 py-3">
                        <span className={cn('px-2 py-1 rounded text-xs font-medium', statusColor(unit.status))}>
                          {UNIT_STATUSES.find((s) => s.value === unit.status)?.label ?? unit.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {format(new Date(unit.received_at), 'PP')}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/units/${unit.id}`}
                          className="text-sm font-medium text-primary hover:underline flex items-center justify-end gap-1"
                        >
                          View
                          <ArrowLeft className="h-3 w-3 rotate-180" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {hasMore && (
              <div className="p-4 border-t">
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={loading}
                  className="w-full px-4 py-2 border rounded-lg text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading more...
                    </span>
                  ) : (
                    'Load More'
                  )}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}