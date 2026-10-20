import React, { useState, useEffect } from 'react'
import { X, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import { cn } from '@/utils/cn'
import { createOverride } from '@/api/decision'
import { channelLabel } from '@/types/decision'

interface OverrideDialogProps {
  decisionId: string
  recommendedChannel: string
  availableChannels: string[]
  open: boolean
  onClose: () => void
  onSuccess?: (message: string) => void
}

/**
 * Dialog for overriding a decision recommendation.
 *
 * The reason is mandatory: an override without a reason cannot feed the
 * regret or calibration analysis, so the submit button stays disabled until
 * one is typed.
 */
export function OverrideDialog({
  decisionId,
  recommendedChannel,
  availableChannels,
  open,
  onClose,
  onSuccess,
}: OverrideDialogProps) {
  const [chosenChannel, setChosenChannel] = useState(recommendedChannel)
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Reset the form each time the dialog opens
  useEffect(() => {
    if (open) {
      setChosenChannel(recommendedChannel)
      setReason('')
      setError(null)
      setSuccess(false)
    }
  }, [open, recommendedChannel])

  if (!open) return null

  const trimmedReason = reason.trim()
  const canSubmit = trimmedReason.length > 0 && chosenChannel.length > 0 && !submitting

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

    setSubmitting(true)
    setError(null)

    try {
      await createOverride(decisionId, {
        chosen_channel: chosenChannel,
        reason_text: trimmedReason,
      })
      setSuccess(true)
      onSuccess?.(`Override recorded: ${channelLabel(chosenChannel)}`)
      // Give the operator a moment to see the confirmation
      setTimeout(() => {
        onClose()
      }, 1200)
    } catch (err) {
      const apiError = err as { response?: { status?: number; data?: { detail?: unknown } } }
      if (apiError.response?.status === 422) {
        setError('A reason is required to override a decision.')
      } else if (apiError.response?.status === 404) {
        setError('Decision not found.')
      } else {
        setError('Failed to record the override. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const isRecommended = chosenChannel === recommendedChannel

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="override-dialog-title"
    >
      <div className="w-full max-w-lg rounded-lg border bg-card p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 id="override-dialog-title" className="text-lg font-semibold">
              Override recommendation
            </h2>
            <p className="text-muted-foreground mt-1 text-sm">
              The engine recommended{' '}
              <span className="font-medium text-foreground">
                {channelLabel(recommendedChannel)}
              </span>
              . Record what you actually did and why.
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
            <span className="text-sm">Override recorded.</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Channel selection */}
            <div>
              <label htmlFor="override-channel" className="mb-1 block text-sm font-medium">
                Channel used <span className="text-red-500">*</span>
              </label>
              <select
                id="override-channel"
                value={chosenChannel}
                onChange={(e) => setChosenChannel(e.target.value)}
                className="w-full rounded-lg border bg-background px-3 py-2 focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              >
                {availableChannels.map((channel) => (
                  <option key={channel} value={channel}>
                    {channelLabel(channel)}
                    {channel === recommendedChannel ? ' (recommended)' : ''}
                  </option>
                ))}
              </select>
              {isRecommended && (
                <p className="mt-1 text-xs text-muted-foreground">
                  You are keeping the recommended channel. The reason is still required so the
                  outcome can be compared.
                </p>
              )}
            </div>

            {/* Reason */}
            <div>
              <label htmlFor="override-reason" className="mb-1 block text-sm font-medium">
                Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                id="override-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={4}
                placeholder="Why was the recommendation overridden?"
                className={cn(
                  'w-full rounded-lg border bg-background px-3 py-2',
                  'focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent',
                  'placeholder:text-muted-foreground'
                )}
              />
              <p className="mt-1 text-xs text-muted-foreground">
                This reason feeds the regret and calibration analysis. Be specific.
              </p>
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
                disabled={!canSubmit}
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
                  'Record override'
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
