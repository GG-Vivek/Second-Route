/**
 * The offline submission queue (F5.5).
 *
 * When an inspection is completed but the network is unavailable, the
 * submission is written to IndexedDB instead of being sent. The queue is
 * drained when connectivity returns, oldest entry first, so inspections
 * reach the server in the order the inspector completed them.
 *
 * An entry leaves the queue only when the server has accepted it. A
 * network failure leaves the entry queued and retryable; a rejection
 * (validation error, missing unit) marks the entry as failed so the queue
 * does not spin on it forever.
 */

import { QUEUE_STORE, getOfflineDb } from './db'
import { createInspection } from '@/api/intake'
import type { CreateInspectionRequest } from '@/types/intake'
import type { QueuedInspection, SyncResult, SyncSummary } from './types'

/** Sends one queued inspection to the server. */
export type InspectionSender = (
  unitId: string,
  payload: CreateInspectionRequest
) => Promise<void>

/** An error carrying the HTTP status the server replied with. */
export class HttpStatusError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'HttpStatusError'
    this.status = status
  }
}

/**
 * Enqueue a completed inspection for later delivery.
 */
export async function enqueueInspection(
  unitId: string,
  payload: CreateInspectionRequest
): Promise<QueuedInspection> {
  const db = await getOfflineDb()
  const entry: QueuedInspection = {
    id: crypto.randomUUID(),
    unitId,
    payload,
    createdAt: new Date().toISOString(),
    attempts: 0,
    lastError: null,
    status: 'pending',
  }
  await db.put(QUEUE_STORE, entry)
  return entry
}

/**
 * Return every queued inspection, oldest first.
 */
export async function listQueue(): Promise<QueuedInspection[]> {
  const db = await getOfflineDb()
  const entries = await db.getAll(QUEUE_STORE)
  return entries.sort((a, b) => a.createdAt.localeCompare(b.createdAt))
}

/**
 * Return the number of queued inspections.
 */
export async function queueSize(): Promise<number> {
  const db = await getOfflineDb()
  return db.count(QUEUE_STORE)
}

/**
 * Remove every queued inspection.
 */
export async function clearQueue(): Promise<void> {
  const db = await getOfflineDb()
  await db.clear(QUEUE_STORE)
}

/**
 * Remove one queued inspection.
 */
export async function removeFromQueue(id: string): Promise<void> {
  const db = await getOfflineDb()
  await db.delete(QUEUE_STORE, id)
}

/**
 * Classify a failure raised by the sender.
 *
 * A failure without an HTTP status is a network problem: the entry stays
 * queued. A 4xx status means the server will never accept this payload, so
 * the entry is marked failed.
 */
function classifyFailure(error: unknown): { retryable: boolean; message: string } {
  if (error instanceof HttpStatusError) {
    const retryable = error.status >= 500
    return {
      retryable,
      message: error.message || `Server responded with ${error.status}`,
    }
  }
  if (error instanceof Error) {
    // No HTTP status means the request never reached the server.
    return { retryable: true, message: error.message || 'Network error' }
  }
  return { retryable: true, message: 'Network error' }
}

/**
 * Drain the queue.
 *
 * Entries are processed oldest first. Every entry is attempted: a
 * permanently rejected entry is marked failed and skipped rather than
 * blocking the rest of the queue, because a later entry belongs to a
 * different unit and can still be delivered. An entry that could not be
 * delivered because the network is down stays queued and is retried on the
 * next sync.
 *
 * Args:
 *   send: The function used to deliver one entry. Defaults to the real API
 *     call; tests inject a stub.
 *
 * Returns:
 * A summary of what was synced, rejected, and left queued.
 */
export async function syncQueue(send?: InspectionSender): Promise<SyncSummary> {
  const sender = send ?? defaultSender
  const summary: SyncSummary = { synced: 0, rejected: 0, offline: 0 }

  const entries = await listQueue()
  for (const entry of entries) {
    const result = await syncEntry(entry, sender)

    if (result.status === 'synced') {
      summary.synced += 1
      await removeFromQueue(entry.id)
    } else if (result.status === 'rejected') {
      summary.rejected += 1
    } else {
      summary.offline += 1
    }
  }

  return summary
}

/**
 * Deliver a single queued entry.
 *
 * On failure the entry is updated in place with the attempt count and the
 * error message, and its status records whether it can still be retried.
 */
export async function syncEntry(
  entry: QueuedInspection,
  send?: InspectionSender
): Promise<SyncResult> {
  const sender = send ?? defaultSender
  const db = await getOfflineDb()

  try {
    await sender(entry.unitId, entry.payload)
    return { status: 'synced', entry }
  } catch (error: unknown) {
    const { retryable, message } = classifyFailure(error)

    const updated: QueuedInspection = {
      ...entry,
      attempts: entry.attempts + 1,
      lastError: message,
      status: retryable ? 'pending' : 'failed',
    }
    await db.put(QUEUE_STORE, updated)

    if (retryable) {
      return { status: 'offline', entry: updated, error: message }
    }
    return { status: 'rejected', entry: updated, error: message }
  }
}

/**
 * The default sender: POST the inspection to the server.
 */
async function defaultSender(
  unitId: string,
  payload: CreateInspectionRequest
): Promise<void> {
  try {
    await createInspection(unitId, payload)
  } catch (error: unknown) {
    throw toStatusError(error)
  }
}

/**
 * Turn an axios error into an `HttpStatusError` so the queue can tell a
 * rejected payload from an unreachable server.
 */
function toStatusError(error: unknown): unknown {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { status?: number; data?: { detail?: unknown } } })
      .response
    if (response?.status) {
      const detail = response.data?.detail
      const message =
        typeof detail === 'string' ? detail : `Server responded with ${response.status}`
      return new HttpStatusError(response.status, message)
    }
  }
  return error
}
