/**
 * Submission helpers that decide between sending now and queueing (F5.5).
 *
 * The rule is simple: try to send, and queue if the network is down. A
 * queued submission is only removed once the server has confirmed it, so
 * nothing is lost between the moment the inspector taps submit and the
 * moment the server accepts the write.
 */

import { createInspection } from '@/api/intake'
import { deleteDraft } from './drafts'
import { enqueueInspection, type InspectionSender } from './queue'
import type { CreateInspectionRequest } from '@/types/intake'

/** What happened to a submitted inspection. */
export type SubmitOutcome =
  /** The server accepted the inspection. */
  | { status: 'submitted' }
  /** The inspection was queued because the network is unavailable. */
  | { status: 'queued'; reason: string }
  /** The server rejected the payload. */
  | { status: 'rejected'; reason: string }

/**
 * Submit an inspection, queueing it when the network is unavailable.
 *
 * Args:
 *   unitId: The unit the inspection belongs to.
 *   payload: The inspection payload.
 *   isOnline: Whether the browser currently believes it is online.
 *   send: The function used to deliver the inspection. Defaults to the real
 *     API call; tests inject a stub.
 *
 * Returns:
 * Whether the inspection was submitted, queued, or rejected.
 */
export async function submitInspection(
  unitId: string,
  payload: CreateInspectionRequest,
  isOnline: boolean,
  send?: InspectionSender
): Promise<SubmitOutcome> {
  const sender = send ?? defaultSender

  if (!isOnline) {
    await enqueueInspection(unitId, payload)
    return { status: 'queued', reason: 'No network connection' }
  }

  try {
    await sender(unitId, payload)
    await deleteDraft(unitId)
    return { status: 'submitted' }
  } catch (error: unknown) {
    // A network failure means the request never reached the server, so the
    // inspection is queued rather than lost. A server rejection is a
    // problem with the payload and is reported to the inspector.
    if (isNetworkError(error)) {
      await enqueueInspection(unitId, payload)
      return { status: 'queued', reason: 'Network unavailable' }
    }
    return { status: 'rejected', reason: describeError(error) }
  }
}

async function defaultSender(
  unitId: string,
  payload: CreateInspectionRequest
): Promise<void> {
  await createInspection(unitId, payload)
}

/**
 * Whether the failure means the request never reached the server.
 */
export function isNetworkError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const candidate = error as { response?: unknown; code?: unknown; message?: unknown }
  if (candidate.response !== undefined) return false
  if (candidate.code === 'ERR_NETWORK' || candidate.code === 'ECONNABORTED') return true
  if (typeof candidate.message === 'string' && /network/i.test(candidate.message)) return true
  return false
}

/**
 * A human-readable description of a failure.
 */
export function describeError(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { status?: number; data?: { detail?: unknown } } })
      .response
    const detail = response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined
      if (first?.msg) return first.msg
    }
    if (response?.status === 404) return 'Unit not found'
    if (response?.status) return `Server responded with ${response.status}`
  }
  if (error instanceof Error) return error.message
  return 'Failed to create inspection'
}
