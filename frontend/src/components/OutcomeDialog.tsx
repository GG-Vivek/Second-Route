import React, { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle2, ClipboardCheck, Loader2 } from 'lucide-react'
import { cn } from '@/utils/cn'
import { createOutcome } from '@/api/decision'
import { channelLabel } from '@/types/decision'
import { Button, Dialog, Field, inputClass, selectClass } from '@/components/ui'

interface OutcomeDialogProps {
  unitId: string
  decisionId: string | null
  recommendedChannel: string
  availableChannels: string[]
  open: boolean
  onClose: () => void
  onSuccess?: (message: string) => void
}

const FINAL_STATUSES = ['sold', 'recycled', 'donated', 'returned_to_vendor', 'scrapped']

/**
 * Dialog for recording what actually happened to a unit.
 *
 * These are realized numbers, not predictions. They feed the regret and
 * calibration analysis, so the channel used and the final status are both
 * required.
 */
export function OutcomeDialog({
  unitId,
  decisionId,
  recommendedChannel,
  availableChannels,
  open,
  onClose,
  onSuccess,
}: OutcomeDialogProps) {
  const [channel, setChannel] = useState(recommendedChannel)
  const [salePrice, setSalePrice] = useState('')
  const [fees, setFees] = useState('')
  const [repair, setRepair] = useState('')
  const [logistics, setLogistics] = useState('')
  const [days, setDays] = useState('')
  const [finalStatus, setFinalStatus] = useState('sold')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (open) {
      setChannel(recommendedChannel)
      setSalePrice('')
      setFees('')
      setRepair('')
      setLogistics('')
      setDays('')
      setFinalStatus('sold')
      setError(null)
      setSuccess(false)
    }
  }, [open, recommendedChannel])

  const num = (value: string) => Number(value)
  const valid =
    salePrice !== '' &&
    fees !== '' &&
    repair !== '' &&
    logistics !== '' &&
    days !== '' &&
    num(salePrice) >= 0 &&
    num(fees) >= 0 &&
    num(repair) >= 0 &&
    num(logistics) >= 0 &&
    num(days) >= 0 &&
    channel.length > 0 &&
    finalStatus.length > 0

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!valid) return

    setSubmitting(true)
    setError(null)

    try {
      const outcome = await createOutcome(unitId, {
        channel_taken: channel,
        sale_price: num(salePrice),
        fees_actual: num(fees),
        repair_cost_actual: num(repair),
        logistics_actual: num(logistics),
        days_to_disposition: num(days),
        final_status: finalStatus,
        ...(decisionId ? { decision_id: decisionId } : {}),
      })
      setSuccess(true)
      onSuccess?.(
        `Outcome recorded: ${channelLabel(outcome.channel_taken)} - net $${outcome.net.toFixed(2)}`
      )
      setTimeout(() => {
        onClose()
      }, 1400)
    } catch (err) {
      const apiError = err as { response?: { status?: number } }
      if (apiError.response?.status === 404) {
        setError('This unit has no decision to link the outcome to.')
      } else if (apiError.response?.status === 422) {
        setError('Check the numbers: they must be zero or greater.')
      } else {
        setError('The outcome could not be recorded. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const netPreview =
    salePrice !== '' && fees !== '' && repair !== '' && logistics !== ''
      ? num(salePrice) - num(fees) - num(repair) - num(logistics)
      : null

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Record the outcome"
      description="What actually happened. These numbers are compared against the prediction."
    >
      {success ? (
        <div className="flex items-center gap-2 rounded-2xl bg-tip-container p-4 text-on-tip-container">
          <CheckCircle2 className="size-5 shrink-0" aria-hidden="true" />
          <span className="text-sm">Outcome recorded.</span>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Channel used" required>
              {({ id }) => (
                <select
                  id={id}
                  value={channel}
                  onChange={(e) => setChannel(e.target.value)}
                  className={cn(selectClass)}
                >
                  {availableChannels.map((option) => (
                    <option key={option} value={option}>
                      {channelLabel(option)}
                      {option === recommendedChannel ? ' (recommended)' : ''}
                    </option>
                  ))}
                </select>
              )}
            </Field>

            <Field label="Final status" required>
              {({ id }) => (
                <select
                  id={id}
                  value={finalStatus}
                  onChange={(e) => setFinalStatus(e.target.value)}
                  className={cn(selectClass)}
                >
                  {FINAL_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {status.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              )}
            </Field>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Sale price" required>
              {({ id }) => (
                <input
                  id={id}
                  type="number"
                  min="0"
                  step="0.01"
                  value={salePrice}
                  onChange={(e) => setSalePrice(e.target.value)}
                  className={inputClass}
                />
              )}
            </Field>
            <Field label="Fees" required>
              {({ id }) => (
                <input
                  id={id}
                  type="number"
                  min="0"
                  step="0.01"
                  value={fees}
                  onChange={(e) => setFees(e.target.value)}
                  className={inputClass}
                />
              )}
            </Field>
            <Field label="Repair cost" required>
              {({ id }) => (
                <input
                  id={id}
                  type="number"
                  min="0"
                  step="0.01"
                  value={repair}
                  onChange={(e) => setRepair(e.target.value)}
                  className={inputClass}
                />
              )}
            </Field>
            <Field label="Logistics cost" required>
              {({ id }) => (
                <input
                  id={id}
                  type="number"
                  min="0"
                  step="0.01"
                  value={logistics}
                  onChange={(e) => setLogistics(e.target.value)}
                  className={inputClass}
                />
              )}
            </Field>
            <Field label="Days to disposition" required>
              {({ id }) => (
                <input
                  id={id}
                  type="number"
                  min="0"
                  step="1"
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                  className={inputClass}
                />
              )}
            </Field>
            <div className="flex items-end">
              <div className="w-full rounded-2xl bg-muted p-3">
                <p className="text-xs text-muted-foreground">Realized net</p>
                <p
                  className="font-mono text-lg font-semibold"
                  data-testid="outcome-net-preview"
                >
                  {netPreview === null ? '—' : `$${netPreview.toFixed(2)}`}
                </p>
              </div>
            </div>
          </div>

          {error && (
            <div
              className="flex items-center gap-2 rounded-2xl bg-caution-container p-3 text-on-caution-container"
              role="alert"
            >
              <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <div className="flex justify-end gap-2 border-t pt-4">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={!valid || submitting}>
              {submitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Recording...
                </>
              ) : (
                <>
                  <ClipboardCheck className="size-4" aria-hidden="true" />
                  Record outcome
                </>
              )}
            </Button>
          </div>
        </form>
      )}
    </Dialog>
  )
}
