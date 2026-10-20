import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, AlertCircle, CloudOff, WifiOff } from 'lucide-react'
import { cn } from '@/utils/cn'
import {
  getUnit,
  type UnitDetail,
  type CreateInspectionRequest,
  COSMETIC_GRADES,
  ACTIVATION_LOCK_OPTIONS,
  FUNCTIONAL_TESTS,
  ACCESSORIES,
} from '@/api/intake'
import { getDraft, saveDraft } from '@/offline/drafts'
import { useOffline } from '@/offline/useOffline'
import { submitInspection } from '@/offline/submit'
import type { InspectionFormValues } from '@/offline/types'

export function NewInspectionPage() {
  const { id: unitId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { isOnline, pendingCount, refreshPendingCount } = useOffline()

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
  const [queued, setQueued] = useState(false)
  const [draftRestored, setDraftRestored] = useState(false)
  // Set once the inspector changes any field, so the autosave does not
  // write an empty draft for every unit that is merely opened.
  const [touched, setTouched] = useState(false)

  // Validation
  const [batteryHealthError, setBatteryHealthError] = useState<string | null>(null)

  // Tracks whether the form has been restored from a saved draft, so the
  // autosave does not immediately overwrite it with empty values.
  const restoredRef = useRef(false)

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

  // Restore a saved draft, if the inspector left one for this unit.
  useEffect(() => {
    if (!unitId) return
    const unit = unitId
    let cancelled = false

    async function restore() {
      try {
        const draft = await getDraft(unit)
        if (!draft || cancelled) return
        setBatteryHealth(draft.values.battery_health_pct)
        setBatteryCycles(draft.values.battery_cycles)
        setCosmeticGrade(draft.values.cosmetic_grade)
        setActivationLock(draft.values.activation_lock)
        setFunctionalTests(draft.values.functional_tests_json)
        setAccessories(draft.values.accessories_json)
        setNotes(draft.values.notes)
        setDraftRestored(true)
        restoredRef.current = true
      } catch {
        // A storage failure must not block the form; the inspector can
        // simply re-enter the values.
      }
    }
    void restore()

    return () => {
      cancelled = true
    }
  }, [unitId])

  // Autosave the form so a disconnect or crash never loses the work.
  //
  // The draft is only written once the inspector has actually changed
  // something, so merely opening a unit does not leave an empty draft
  // behind for every unit in the queue.
  useEffect(() => {
    if (!unitId) return
    if (!touched && !restoredRef.current) return

    const values: InspectionFormValues = {
      battery_health_pct: batteryHealth,
      battery_cycles: batteryCycles,
      cosmetic_grade: cosmeticGrade,
      functional_tests_json: functionalTests,
      activation_lock: activationLock,
      accessories_json: accessories,
      notes,
    }

    const timer = setTimeout(() => {
      void saveDraft(unitId, values).catch(() => {
        // Autosave is best effort; a failure here must not interrupt the
        // inspector.
      })
    }, 500)

    return () => clearTimeout(timer)
  }, [
    unitId,
    touched,
    batteryHealth,
    batteryCycles,
    cosmeticGrade,
    functionalTests,
    activationLock,
    accessories,
    notes,
  ])

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
    setQueued(false)

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
        // Mark the inspection as offline-created so the server can tell it
        // apart from one entered live, and so conflicts are audited.
        offline_created: !isOnline,
      }

      const outcome = await submitInspection(unitId, inspectionData, isOnline)

      if (outcome.status === 'submitted') {
        navigate(`/units/${unitId}`)
        return
      }

      if (outcome.status === 'queued') {
        setQueued(true)
        await refreshPendingCount()
        return
      }

      setSubmitError(outcome.reason)
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

      {/* Offline status */}
      {!isOnline && (
        <div
          role="status"
          className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 flex items-start gap-3"
        >
          <WifiOff className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">You are offline</p>
            <p className="text-sm">
              Your work is saved on this device and will sync automatically when the connection
              returns.
              {pendingCount > 0 && ` ${pendingCount} inspection(s) are waiting to sync.`}
            </p>
          </div>
        </div>
      )}

      {draftRestored && (
        <div
          role="status"
          className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-blue-900 flex items-start gap-3"
        >
          <CloudOff className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Draft restored</p>
            <p className="text-sm">A saved draft for this unit was restored.</p>
          </div>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        onChange={() => setTouched(true)}
        className="space-y-6"
      >
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
                {isOnline ? 'Creating...' : 'Saving...'}
              </>
            ) : isOnline ? (
              'Create Inspection'
            ) : (
              'Save Offline'
            )}
          </button>
        </div>

        {submitError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{submitError}</span>
          </div>
        )}

        {queued && (
          <div
            role="status"
            className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 flex items-center gap-2"
          >
            <CloudOff className="h-5 w-5 flex-shrink-0" />
            <span>
              Inspection saved on this device. It will be sent automatically when you are back
              online.
            </span>
          </div>
        )}
      </form>
    </div>
  )
}