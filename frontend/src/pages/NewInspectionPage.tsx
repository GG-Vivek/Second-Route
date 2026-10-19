import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react'
import { cn } from '@/utils/cn'
import {
  createInspection,
  getUnit,
  type UnitDetail,
  type CreateInspectionRequest,
  COSMETIC_GRADES,
  ACTIVATION_LOCK_OPTIONS,
  FUNCTIONAL_TESTS,
  ACCESSORIES,
} from '@/api/intake'

export function NewInspectionPage() {
  const { id: unitId } = useParams<{ id: string }>()
  const navigate = useNavigate()

  // Form state
  const [batteryHealth, setBatteryHealth] = useState('')
  const [batteryCycles, setBatteryCycles] = useState('')
  const [cosmeticGrade, setCosmeticGrade] = useState('')
  const [activationLock, setActivationLock] = useState<'none' | 'present' | 'unknown'>('unknown')
  const [functionalTests, setFunctionalTests] = useState<Record<string, boolean>>({})
  const [accessories, setAccessories] = useState<Record<string, boolean>>({})
  const [notes, setNotes] = useState('')

  // Unit data
  const [unit, setUnit] = useState<UnitDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // Validation
  const [batteryHealthError, setBatteryHealthError] = useState<string | null>(null)

  // Load unit
  useEffect(() => {
    async function fetchUnit() {
      if (!unitId) return
      try {
        setLoading(true)
        const data = await getUnit(unitId)
        setUnit(data)
        setError(null)
      } catch (err: unknown) {
        const error = err as { response?: { status: number } }
        if (error.response?.status === 404) {
          setError('Unit not found')
        } else {
          setError('Failed to load unit')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchUnit()
  }, [unitId])

  // Initialize functional tests and accessories with defaults
  useEffect(() => {
    const initialFunctionalTests: Record<string, boolean> = {}
    FUNCTIONAL_TESTS.forEach((test) => {
      initialFunctionalTests[test.key] = false
    })
    setFunctionalTests(initialFunctionalTests)

    const initialAccessories: Record<string, boolean> = {}
    ACCESSORIES.forEach((acc) => {
      initialAccessories[acc.key] = false
    })
    setAccessories(initialAccessories)
  }, [])

  // Validation
  const validateBatteryHealth = useCallback((value: string) => {
    const num = parseFloat(value)
    if (value && (isNaN(num) || num < 0 || num > 100)) {
      setBatteryHealthError('Battery health must be between 0 and 100')
      return false
    }
    setBatteryHealthError(null)
    return true
  }, [])

  const handleBatteryHealthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setBatteryHealth(value)
    validateBatteryHealth(value)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitError(null)

    if (!unitId) return

    // Validate required fields
    if (!batteryHealth) {
      setSubmitError('Battery health is required')
      return
    }
    if (!validateBatteryHealth(batteryHealth)) {
      setSubmitError('Please fix battery health value')
      return
    }
    if (!cosmeticGrade) {
      setSubmitError('Cosmetic grade is required')
      return
    }

    setSubmitting(true)
    try {
      const inspectionData: CreateInspectionRequest = {
        battery_health_pct: batteryHealth,
        battery_cycles: batteryCycles || undefined,
        cosmetic_grade: cosmeticGrade,
        functional_tests_json: functionalTests,
        activation_lock: activationLock,
        accessories_json: accessories,
        notes: notes || undefined,
      }

      await createInspection(unitId, inspectionData)
      navigate(`/units/${unitId}`)
    } catch (err: unknown) {
      const error = err as { response?: { status: number; data?: { detail?: string } } }
      if (error.response?.status === 422) {
        const detail = error.response.data?.detail
        if (Array.isArray(detail)) {
          const msg = detail.find((d) => d.loc.includes('battery_health_pct'))
          setSubmitError(msg?.msg ?? 'Invalid data. Please check your inputs.')
        } else {
          setSubmitError('Invalid data. Please check your inputs.')
        }
      } else if (error.response?.status === 404) {
        setSubmitError('Unit not found')
      } else {
        setSubmitError('Failed to create inspection. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleBack = () => {
    if (unitId) navigate(`/units/${unitId}`)
    else navigate(-1)
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

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={handleBack} className="p-2 rounded-lg hover:bg-accent transition-colors">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold">New Inspection</h1>
          <p className="text-muted-foreground">
            {unit ? `${unit.sku?.family} ${unit.sku?.model_name} • ${unit.serial ?? 'No serial'}` : 'Loading...'}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Battery Health */}
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">Battery Information</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="batteryHealth" className="block text-sm font-medium mb-1">
                Battery Health % <span className="text-red-500">*</span>
              </label>
              <input
                id="batteryHealth"
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={batteryHealth}
                onChange={handleBatteryHealthChange}
                onBlur={(e) => validateBatteryHealth(e.target.value)}
                placeholder="e.g., 95.5"
                className={cn(
                  'w-full px-4 py-2 border rounded-lg bg-background',
                  'focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent',
                  batteryHealthError && 'border-red-500 focus:ring-red-500'
                )}
              />
              {batteryHealthError && (
                <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {batteryHealthError}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="batteryCycles" className="block text-sm font-medium mb-1">
                Battery Cycles
              </label>
              <input
                id="batteryCycles"
                type="number"
                min="0"
                value={batteryCycles}
                onChange={(e) => setBatteryCycles(e.target.value)}
                placeholder="e.g., 150"
                className="w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Cosmetic Grade */}
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">Cosmetic Grade <span className="text-red-500">*</span></h2>
          <div className="grid grid-cols-4 gap-3">
            {COSMETIC_GRADES.map((grade) => (
              <label
                key={grade}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 border rounded-lg cursor-pointer transition-colors',
                  cosmeticGrade === grade
                    ? 'border-primary bg-primary/5 text-primary'
                    : 'hover:border-accent hover:bg-accent/50'
                )}
              >
                <input
                  type="radio"
                  name="cosmeticGrade"
                  value={grade}
                  checked={cosmeticGrade === grade}
                  onChange={() => setCosmeticGrade(grade)}
                  className="sr-only"
                />
                <span className="text-3xl font-bold">{grade}</span>
                <span className="text-xs text-muted-foreground">
                  {grade === 'A' && 'Excellent'}
                  {grade === 'B' && 'Good'}
                  {grade === 'C' && 'Fair'}
                  {grade === 'D' && 'Poor'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Activation Lock */}
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">Activation Lock</h2>
          <div className="grid grid-cols-3 gap-3">
            {ACTIVATION_LOCK_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 border rounded-lg cursor-pointer transition-colors',
                  activationLock === option.value
                    ? 'border-primary bg-primary/5 text-primary'
                    : 'hover:border-accent hover:bg-accent/50'
                )}
              >
                <input
                  type="radio"
                  name="activationLock"
                  value={option.value}
                  checked={activationLock === option.value}
                  onChange={() => setActivationLock(option.value)}
                  className="sr-only"
                />
                <span className="font-medium">{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Functional Tests */}
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">Functional Tests</h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {FUNCTIONAL_TESTS.map((test) => (
              <label key={test.key} className="flex items-center gap-2 p-3 border rounded-lg hover:bg-accent/50 transition-colors cursor-pointer">
                <input
                  type="checkbox"
                  checked={functionalTests[test.key]}
                  onChange={(e) => setFunctionalTests((prev) => ({ ...prev, [test.key]: e.target.checked }))}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm font-medium">{test.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Accessories */}
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">Accessories</h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {ACCESSORIES.map((acc) => (
              <label key={acc.key} className="flex items-center gap-2 p-3 border rounded-lg hover:bg-accent/50 transition-colors cursor-pointer">
                <input
                  type="checkbox"
                  checked={accessories[acc.key]}
                  onChange={(e) => setAccessories((prev) => ({ ...prev, [acc.key]: e.target.checked }))}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm font-medium">{acc.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Notes */}
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">Notes</h2>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Any additional notes about this inspection..."
            rows={3}
            className="w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
          />
        </div>

        {/* Submit */}
        <div className="flex items-center gap-4 pt-4 border-t">
          <button type="button" onClick={handleBack} className="px-4 py-2 border rounded-lg hover:bg-accent transition-colors">
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className={cn(
              'ml-auto px-6 py-2 rounded-lg font-medium transition-colors',
              'bg-primary text-primary-foreground hover:bg-primary/90',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {submitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Inspection'
            )}
          </button>
        </div>

        {submitError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{submitError}</span>
          </div>
        )}
      </form>
    </div>
  )
}