import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Loader2, AlertCircle, CheckCircle, FileText, Camera, ChevronDown, ChevronUp, Eye } from 'lucide-react'
import { format } from 'date-fns'
import { cn } from '@/utils/cn'
import { getUnit, updateUnitStatus, type UnitDetail, type UnitStatus, type Photo, UNIT_STATUSES, gradeColor, lockColor } from '@/api/intake'

export function UnitDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [unit, setUnit] = useState<UnitDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updatingStatus, setUpdatingStatus] = useState(false)
  const [expandedInspection, setExpandedInspection] = useState<string | null>(null)

  useEffect(() => {
    async function fetchUnit() {
      if (!id) return
      try {
        setLoading(true)
        const data = await getUnit(id)
        setUnit(data)
        setError(null)
      } catch (err: unknown) {
        const error = err as { response?: { status: number } }
        if (error.response?.status === 404) {
          setError('Unit not found')
        } else {
          setError('Failed to load unit details')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchUnit()
  }, [id])

  const handleStatusChange = async (newStatus: UnitStatus) => {
    if (!id) return
    setUpdatingStatus(true)
    try {
      const updated = await updateUnitStatus(id, { status: newStatus })
      setUnit((prev) => (prev ? { ...prev, status: updated.status } : null))
    } catch (err) {
      console.error('Failed to update status:', err)
      alert('Failed to update status')
    } finally {
      setUpdatingStatus(false)
    }
  }

  const handleBack = () => navigate(-1)

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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 text-primary animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Error</h2>
        <p className="text-muted-foreground mb-6">{error}</p>
        <button onClick={handleBack} className="px-4 py-2 border rounded-lg hover:bg-accent transition-colors">
          Go Back
        </button>
      </div>
    )
  }

  if (!unit) return null

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <button onClick={handleBack} className="p-2 rounded-lg hover:bg-accent transition-colors">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold">Unit {unit.id.slice(0, 8)}...</h1>
            <p className="text-muted-foreground">
              {unit.sku ? `${unit.sku.family} ${unit.sku.model_name} (${unit.sku.year})` : 'Unknown SKU'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={unit.status}
            onChange={(e) => handleStatusChange(e.target.value as UnitStatus)}
            disabled={updatingStatus}
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium border',
              statusColor(unit.status)
            )}
          >
            {UNIT_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <Link
            to={`/units/${unit.id}/inspection/new`}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <FileText className="h-4 w-4" />
            Add Inspection
          </Link>
        </div>
      </div>

      {/* Unit Info Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <InfoCard title="Serial Number" value={unit.serial ?? '—'} icon={<Eye className="h-5 w-5" />} />
        <InfoCard title="Return Reason" value={unit.return_reason_code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())} icon={<AlertCircle className="h-5 w-5" />} />
        <InfoCard title="Order Channel" value={unit.order_channel} icon={<CheckCircle className="h-5 w-5" />} />
        <InfoCard title="Received" value={format(new Date(unit.received_at), 'PPp')} icon={<FileText className="h-5 w-5" />} />
      </div>

      {/* SKU Details */}
      {unit.sku && (
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">SKU Details</h2>
          <div className="grid gap-3 md:grid-cols-3">
            <DetailRow label="Family" value={unit.sku.family} />
            <DetailRow label="Model" value={unit.sku.model_name} />
            <DetailRow label="Year" value={unit.sku.year} />
            <DetailRow label="Storage" value={unit.sku.storage_gb} />
            <DetailRow label="RAM" value={unit.sku.ram_gb} />
            <DetailRow label="Color" value={unit.sku.color} />
            <DetailRow label="Region" value={unit.sku.region} />
            <DetailRow label="Source" value={unit.sku.source} />
            <DetailRow label="As Of" value={unit.sku.as_of} />
          </div>
        </div>
      )}

      {/* Inspections */}
      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        <div className="p-6 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold">Inspections ({unit.inspections.length})</h2>
          <Link
            to={`/units/${unit.id}/inspection/new`}
            className="px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <FileText className="h-4 w-4" />
            Add Inspection
          </Link>
        </div>

        {unit.inspections.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">No inspections yet</p>
            <p className="text-sm">Add the first inspection to begin grading this unit</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {unit.inspections
              .slice()
              .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
              .map((inspection) => (
                <InspectionCard
                  key={inspection.id}
                  inspection={inspection}
                  expanded={expandedInspection === inspection.id}
                  onToggle={() => setExpandedInspection(expandedInspection === inspection.id ? null : inspection.id)}
                />
              ))}
          </div>
        )}
      </div>

      {/* Photos */}
      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        <div className="p-6 border-b">
          <h2 className="text-lg font-semibold">Photos ({unit.photos.length})</h2>
        </div>

        {unit.photos.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            <Camera className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">No photos uploaded</p>
          </div>
        ) : (
          <div className="p-6">
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {unit.photos.map((photo: Photo) => (
                <div key={photo.id} className="relative aspect-square rounded-lg overflow-hidden border bg-muted">
                  <div className="w-full h-full flex items-center justify-center bg-muted">
                    <Camera className="h-12 w-12 text-muted-foreground/50" />
                  </div>
                  <div className="absolute bottom-0 left-0 right-0 p-2 bg-black/60 text-white text-xs">
                    {format(new Date(photo.created_at), 'PPp')}
                  </div>
                  <div className="absolute top-1 right-1 flex gap-1">
                    <span className={cn('px-1.5 py-0.5 rounded text-xs', photo.exif_stripped ? 'bg-green-600' : 'bg-yellow-600')}>
                      {photo.exif_stripped ? 'EXIF Stripped' : 'EXIF Present'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function InfoCard({ title, value, icon }: { title: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">{icon}</div>
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="font-medium text-sm truncate max-w-xs">{value}</p>
        </div>
      </div>
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium text-sm">{value}</p>
    </div>
  )
}

function InspectionCard({
  inspection,
  expanded,
  onToggle,
}: {
  inspection: UnitDetail['inspections'][0]
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 flex-1">
          <button onClick={onToggle} className="p-1 rounded hover:bg-accent transition-colors" aria-expanded={expanded}>
            {expanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
          </button>
          <div>
            <p className="font-medium">Inspection {inspection.id.slice(0, 8)}...</p>
            <p className="text-sm text-muted-foreground">
              {format(new Date(inspection.created_at), 'PPp')}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn('px-2 py-1 rounded text-xs font-medium', gradeColor(inspection.cosmetic_grade))}>
            Grade {inspection.cosmetic_grade}
          </span>
          <span className={cn('px-2 py-1 rounded text-xs font-medium', lockColor(inspection.activation_lock))}>
            {inspection.activation_lock === 'none' ? 'No Lock' : inspection.activation_lock === 'present' ? 'Locked' : 'Unknown'}
          </span>
          <span className="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
            {inspection.battery_health_pct}% Battery
          </span>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <DetailRow label="Battery Health" value={`${inspection.battery_health_pct}%`} />
            <DetailRow label="Battery Cycles" value={inspection.battery_cycles ?? '—'} />
            <DetailRow label="Cosmetic Grade" value={inspection.cosmetic_grade} />
            <DetailRow label="Activation Lock" value={inspection.activation_lock} />
          </div>

          <div>
            <h4 className="font-medium mb-2">Functional Tests</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(inspection.functional_tests_json).map(([key, value]: [string, boolean]) => (
                <span
                  key={key}
                  className={cn(
                    'px-2 py-1 rounded text-xs font-medium',
                    value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  )}
                >
                  {key.replace(/_/g, ' ').replace(/\b\w/g, (letter: string) => letter.toUpperCase())}: {value ? 'Pass' : 'Fail'}
                </span>
              ))}
              {Object.keys(inspection.functional_tests_json).length === 0 && (
                <span className="text-sm text-muted-foreground">No functional tests recorded</span>
              )}
            </div>
          </div>

          <div>
            <h4 className="font-medium mb-2">Accessories</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(inspection.accessories_json).map(([key, value]: [string, boolean]) => (
                <span
                  key={key}
                  className={cn(
                    'px-2 py-1 rounded text-xs font-medium',
                    value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  )}
                >
                  {key.replace(/_/g, ' ').replace(/\b\w/g, (letter: string) => letter.toUpperCase())}: {value ? 'Yes' : 'No'}
                </span>
              ))}
              {Object.keys(inspection.accessories_json).length === 0 && (
                <span className="text-sm text-muted-foreground">No accessories recorded</span>
              )}
            </div>
          </div>

          {inspection.notes && (
            <div className="rounded-lg bg-muted p-4">
              <h4 className="font-medium mb-1">Notes</h4>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">{inspection.notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}