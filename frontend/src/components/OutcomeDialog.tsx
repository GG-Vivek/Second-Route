import React, { useState, useEffect } from 'react'
import { X, Loader2, AlertCircle, CheckCircle, ClipboardCheck } from 'lucide-react'
import { cn } from '@/utils/cn'
import { createOutcome } from '@/api/decision'
import { channelLabel } from '@/types/decision'

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

  if (!open) return null

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
        setError('Failed to record the outcome. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const netPreview =
    salePrice !== '' && fees !== '' && repair !== '' && logistics !== ''
      ? num(salePrice) - num(fees) - num(repair) - num(logistics)
      : null

  const fieldClass =
    'w-full rounded-lg border bg-background px-3 py-2 focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="outcome-dialog-title"
    >
      <div className="w-full max-w-lg rounded-lg border bg-card p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 id="outcome-dialog-title" className="text-lg font-semibold">
              Record the outcome
            </h2>
            <p className="text-muted-foreground mt-1 text-sm">
              What actually happened. These numbers are compared against the prediction.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 hover:bg-accent"
            aria-label="Close dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {success ? (
          <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-4 text-green-800">
            <CheckCircle className="h-5 w-5 flex-shrink-0" />
            <span className="text-sm">Outcome recorded.</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="outcome-channel" className="mb-1 block text-sm font-medium">
                  Channel used <span className="text-red-500">*</span>
                </label>
                <select
                  id="outcome-channel"
                  value={channel}
                  onChange={(e) => setChannel(e.target.value)}
                  className={fieldClass}
                >
                  {availableChannels.map((option) => (
                    <option key={option} value={option}>
                      {channelLabel(option)}
                      {option === recommendedChannel ? ' (recommended)' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="outcome-final-status" className="mb-1 block text-sm font-medium">
                  Final status <span className="text-red-500">*</span>
                </label>
                <select
                  id="outcome-final-status"
                  value={finalStatus}
                  onChange={(e) => setFinalStatus(e.target.value)}
                  className={fieldClass}
                >
                  {FINAL_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {status.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="outcome-sale-price" className="mb-1 block text-sm font-medium">
                  Sale price <span className="text-red-500">*</span>
                </label>
                <input
                  id="outcome-sale-price"
                  type="number"
                  min="0"
                  step="0.01"
                  value={salePrice}
                  onChange={(e) => setSalePrice(e.target.value)}
                  className={fieldClass}
                />
              </div>
              <div>
                <label htmlFor="outcome-fees" className="mb-1 block text-sm font-medium">
                  Fees <span className="text-red-500">*</span>
                </label>
                <input
                  id="outcome-fees"
                  type="number"
                  min="0"
                  step="0.01"
                  value={fees}
                  onChange={(e) => setFees(e.target.value)}
                  className={fieldClass}
                />
              </div>
              <div>
                <label htmlFor="outcome-repair" className="mb-1 block text-sm font-medium">
                  Repair cost <span className="text-red-500">*</span>
                </label>
                <input
                  id="outcome-repair"
                  type="number"
                  min="0"
                  step="0.01"
                  value={repair}
                  onChange={(e) => setRepair(e.target.value)}
                  className={fieldClass}
                />
              </div>
              <div>
                <label htmlFor="outcome-logistics" className="mb-1 block text-sm font-medium">
                  Logistics cost <span className="text-red-500">*</span>
                </label>
                <input
                  id="outcome-logistics"
                  type="number"
                  min="0"
                  step="0.01"
                  value={logistics}
                  onChange={(e) => setLogistics(e.target.value)}
                  className={fieldClass}
                />
              </div>
              <div>
                <label htmlFor="outcome-days" className="mb-1 block text-sm font-medium">
                  Days to disposition <span className="text-red-500">*</span>
                </label>
                <input
                  id="outcome-days"
                  type="number"
                  min="0"
                  step="1"
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                  className={fieldClass}
                />
              </div>
              <div className="flex items-end">
                <div className="w-full rounded-lg bg-muted p-3">
                  <p className="text-xs text-muted-foreground">Realized net</p>
                  <p className="font-mono text-lg font-semibold" data-testid="outcome-net-preview">
                    {netPreview === null ? '—' : `$${netPreview.toFixed(2)}`}
                  </p>
                </div>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}

            <div className="flex justify-end gap-2 border-t pt-4">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!valid || submitting}
                className={cn(
                  'rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
                  'hover:bg-primary/90 transition-colors',
                  'disabled:cursor-not-allowed disabled:opacity-50'
                )}
              >
                {submitting ? (
                  <>
                    <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />
                    Recording...
                  </>
                ) : (
                  <>
                    <ClipboardCheck className="mr-2 inline h-4 w-4" />
                    Record outcome
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
