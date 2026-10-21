import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CloudUpload, Loader2, WifiOff } from 'lucide-react'
import { cn } from '@/utils/cn'
import {
  Button,
  Callout,
  CheckboxGroup,
  Field,
  RadioCards,
  Step,
  Steps,
  StickyActions,
  inputClass,
  textareaClass,
} from '@/components/ui'
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

/** What each grade is called, in the words an inspector would use. */
const GRADE_WORDS: Record<string, string> = {
  A: 'Excellent',
  B: 'Good',
  C: 'Fair',
  D: 'Poor',
}

/**
 * The inspection.
 *
 * The person filling this in is holding the device and looking at it,
 * not at the screen, so the options are shown as choices they can see
 * all at once rather than as a list of checkboxes.
 */
export function NewInspectionPage() {
  const { id: unitId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { isOnline, pendingCount, refreshPendingCount } = useOffline()

  const [batteryHealth, setBatteryHealth] = useState('')
  const [batteryCycles, setBatteryCycles] = useState('')
  const [cosmeticGrade, setCosmeticGrade] = useState('')
  const [activationLock, setActivationLock] = useState<'none' | 'present' | 'unknown'>('unknown')
  const [functionalTests, setFunctionalTests] = useState<Record<string, boolean>>({})
  const [accessories, setAccessories] = useState<Record<string, boolean>>({})
  const [notes, setNotes] = useState('')

  const [unit, setUnit] = useState<UnitDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [queued, setQueued] = useState(false)
  const [draftRestored, setDraftRestored] = useState(false)

  // Set once the inspector changes any field, so that the autosave does
  // not write an empty draft for every unit that is merely opened.
  const [touched, setTouched] = useState(false)
  const [batteryHealthError, setBatteryHealthError] = useState<string | null>(null)

  // Tracks whether the form has been restored from a saved draft, so the
  // autosave does not immediately overwrite it with empty values.
  const restoredRef = useRef(false)

  useEffect(() => {
    async function fetchUnit() {
      if (!unitId) return
      try {
        setLoading(true)
        const data = await getUnit(unitId)
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
  }, [unitId])

  // Every option starts unticked, so that nothing is claimed by accident.
  useEffect(() => {
    setFunctionalTests(
      Object.fromEntries(FUNCTIONAL_TESTS.map((test) => [test.key, false]))
    )
    setAccessories(Object.fromEntries(ACCESSORIES.map((acc) => [acc.key, false])))
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

  // Autosave the form so a disconnect or a crash never loses the work.
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

  const validateBatteryHealth = useCallback((value: string) => {
    const num = parseFloat(value)
    if (value && (isNaN(num) || num < 0 || num > 100)) {
      setBatteryHealthError('Battery health must be between 0 and 100')
      return false
    }
    setBatteryHealthError(null)
    return true
  }, [])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitError(null)
    setQueued(false)

    if (!unitId) return

    if (!batteryHealth) {
      setSubmitError('The battery health is required.')
      return
    }
    if (!validateBatteryHealth(batteryHealth)) {
      setSubmitError('The battery health has to be between 0 and 100.')
      return
    }
    if (!cosmeticGrade) {
      setSubmitError('The cosmetic grade is required.')
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

      const result = await submitInspection(unitId, inspectionData, isOnline)

      if (result.status === 'submitted') {
        navigate(`/units/${unitId}`)
        return
      }

      if (result.status === 'queued') {
        setQueued(true)
        await refreshPendingCount()
        return
      }

      setSubmitError(result.reason)
    } finally {
      setSubmitting(false)
    }
  }

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
        <Callout tone="caution" title="The inspection could not be started">
          <p>{error}</p>
        </Callout>
        <Button variant="outline" className="mt-4" onClick={() => navigate(-1)}>
          Go back
        </Button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} onChange={() => setTouched(true)} className="mx-auto max-w-3xl space-y-8">
      <div className="flex items-start gap-4">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => navigate(unitId ? `/units/${unitId}` : '/units')}
          aria-label="Go back"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">New Inspection</h1>
          <p className="mt-1 text-muted-foreground">
            {unit
              ? `${unit.sku?.family} ${unit.sku?.model_name} - ${unit.serial ?? 'no serial'}`
              : 'Loading...'}
          </p>
        </div>
      </div>

      {!isOnline && (
        <Callout tone="warning" title="You are offline">
          <p>
            Your work is saved on this device and will sync automatically when the connection
            returns.
            {pendingCount > 0 && ` ${pendingCount} inspection(s) are waiting to sync.`}
          </p>
        </Callout>
      )}

      {draftRestored && (
        <Callout tone="note" title="Draft restored">
          <p>A saved draft for this unit was restored.</p>
        </Callout>
      )}

      <Steps>
        <Step
          number={1}
          title="Battery"
          description="The battery health is what decides the grade more than anything else."
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Battery Health %" required error={batteryHealthError}>
              {({ id, describedBy }) => (
                <input
                  id={id}
                  aria-describedby={describedBy}
                  aria-invalid={batteryHealthError ? 'true' : undefined}
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={batteryHealth}
                  onChange={(event) => {
                    setBatteryHealth(event.target.value)
                    validateBatteryHealth(event.target.value)
                  }}
                  onBlur={(event) => validateBatteryHealth(event.target.value)}
                  placeholder="95.5"
                  className={cn(inputClass, batteryHealthError && 'border-destructive')}
                />
              )}
            </Field>

            <Field label="Battery Cycles">
              {({ id }) => (
                <input
                  id={id}
                  type="number"
                  min="0"
                  value={batteryCycles}
                  onChange={(event) => setBatteryCycles(event.target.value)}
                  placeholder="120"
                  className={inputClass}
                />
              )}
            </Field>
          </div>
        </Step>

        <Step
          number={2}
          title="Cosmetic grade"
          description="How the device looks. The photos are taken against this grade."
        >
          <RadioCards
            name="cosmeticGrade"
            label="Cosmetic grade"
            value={cosmeticGrade}
            onChange={setCosmeticGrade}
            options={COSMETIC_GRADES.map((grade) => ({
              value: grade,
              label: grade,
              description: GRADE_WORDS[grade],
            }))}
          />
        </Step>

        <Step
          number={3}
          title="Activation lock"
          description="The flag is stored, never the Apple ID."
        >
          <RadioCards
            name="activationLock"
            label="Activation lock"
            value={activationLock}
            onChange={setActivationLock}
            options={ACTIVATION_LOCK_OPTIONS.map((option) => ({
              value: option.value,
              label: option.label,
            }))}
          />
        </Step>

        <Step
          number={4}
          title="Functional tests"
          description="Tick everything that works. A failure is what the parts channel is priced on."
        >
          <CheckboxGroup
            name="functionalTests"
            value={functionalTests}
            onChange={setFunctionalTests}
            options={FUNCTIONAL_TESTS.map((test) => ({
              key: test.key,
              label: test.label,
            }))}
          />
        </Step>

        <Step
          number={5}
          title="Accessories"
          description="What came back with the device."
        >
          <CheckboxGroup
            name="accessories"
            value={accessories}
            onChange={setAccessories}
            options={ACCESSORIES.map((acc) => ({
              key: acc.key,
              label: acc.label,
            }))}
          />
        </Step>

        <Step
          number={6}
          title="Notes"
          description="Anything the next person should know."
        >
          <Field label="Notes">
            {({ id }) => (
              <textarea
                id={id}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Any additional notes about this inspection..."
                rows={4}
                className={textareaClass}
              />
            )}
          </Field>
        </Step>
      </Steps>

      {submitError && <Callout tone="caution">{submitError}</Callout>}

      {queued && (
        <Callout tone="tip" title="Inspection saved on this device">
          <p className="flex items-center gap-2">
            <CloudUpload className="size-4" aria-hidden="true" />
            It will be sent automatically when you are back online.
          </p>
        </Callout>
      )}

      <StickyActions>
        <Button
          type="button"
          variant="outline"
          onClick={() => navigate(unitId ? `/units/${unitId}` : '/units')}
        >
          Cancel
        </Button>
        {!isOnline && (
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <WifiOff className="size-3.5" aria-hidden="true" />
            Working offline
          </span>
        )}
        <Button type="submit" disabled={submitting} className="ml-auto">
          {submitting ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              {isOnline ? 'Creating...' : 'Saving...'}
            </>
          ) : isOnline ? (
            'Create Inspection'
          ) : (
            'Save Offline'
          )}
        </Button>
      </StickyActions>
    </form>
  )
}
