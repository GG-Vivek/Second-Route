import React, { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import { cn } from '@/utils/cn'
import { createOverride } from '@/api/decision'
import { channelLabel } from '@/types/decision'
import { Button, Dialog, Field, selectClass, textareaClass } from '@/components/ui'

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
      const apiError = err as { response?: { status?: number } }
      if (apiError.response?.status === 422) {
        setError('A reason is required to override a decision.')
      } else if (apiError.response?.status === 404) {
        setError('That decision no longer exists.')
      } else {
        setError('The override could not be recorded. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const isRecommended = chosenChannel === recommendedChannel

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Override recommendation"
      description={`The engine recommended ${channelLabel(
        recommendedChannel
      )}. Record what you actually did and why.`}
    >
      {success ? (
        <div className="flex items-center gap-2 rounded-2xl bg-tip-container p-4 text-on-tip-container">
          <CheckCircle2 className="size-5 shrink-0" aria-hidden="true" />
          <span className="text-sm">Override recorded.</span>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Channel used" required>
            {({ id }) => (
              <select
                id={id}
                value={chosenChannel}
                onChange={(e) => setChosenChannel(e.target.value)}
                className={cn(selectClass)}
              >
                {availableChannels.map((channel) => (
                  <option key={channel} value={channel}>
                    {channelLabel(channel)}
                    {channel === recommendedChannel ? ' (recommended)' : ''}
                  </option>
                ))}
              </select>
            )}
          </Field>

          {isRecommended && (
            <p className="text-xs text-muted-foreground">
              You are keeping the recommended channel. The reason is still required so the
              outcome can be compared.
            </p>
          )}

          <Field
            label="Reason"
            required
            hint="This reason feeds the regret and calibration analysis. Be specific."
          >
            {({ id, describedBy }) => (
              <textarea
                id={id}
                aria-describedby={describedBy}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={4}
                placeholder="Why was the recommendation overridden?"
                className={cn(textareaClass)}
              />
            )}
          </Field>

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
            <Button type="submit" disabled={!canSubmit}>
              {submitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Recording...
                </>
              ) : (
                'Record override'
              )}
            </Button>
          </div>
        </form>
      )}
    </Dialog>
  )
}
