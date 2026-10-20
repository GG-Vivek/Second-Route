/**
 * Types for the offline inspection module (F5.5).
 *
 * The offline store keeps two kinds of records in IndexedDB:
 *
 * - **Drafts**: an in-progress inspection form, keyed by the unit it belongs
 *   to. A draft exists so that a half-finished inspection survives a page
 *   reload, a crash, or a forced disconnect.
 * - **Queue entries**: a completed inspection waiting to be sent to the
 *   server. The queue is the durable hand-off point: a submission is removed
 *   from it only after the server has confirmed the write.
 */

import type { CreateInspectionRequest } from '@/types/intake'

/** The state of the inspection form as the user fills it in. */
export interface InspectionFormValues {
  battery_health_pct: string
  battery_cycles: string
  cosmetic_grade: string
  functional_tests_json: Record<string, boolean>
  activation_lock: 'none' | 'present' | 'unknown'
  accessories_json: Record<string, boolean>
  notes: string
}

/** A locally stored, not-yet-submitted inspection form. */
export interface InspectionDraft {
  /** Client-generated identifier. Stable across edits. */
  id: string
  /** The unit this draft belongs to. */
  unitId: string
  /** The form contents at the time of the last save. */
  values: InspectionFormValues
  /** ISO timestamp of the last save. */
  updatedAt: string
}

/** Lifecycle of a queued submission. */
export type QueueEntryStatus = 'pending' | 'failed'

/** A completed inspection waiting for the network. */
export interface QueuedInspection {
  /** Client-generated identifier, also used as the idempotency key. */
  id: string
  /** The unit the inspection belongs to. */
  unitId: string
  /** The payload to send to the server. */
  payload: CreateInspectionRequest
  /** ISO timestamp of when the entry was enqueued. */
  createdAt: string
  /** How many times a sync attempt has failed. */
  attempts: number
  /** The last failure message, or `null` when the entry has not failed. */
  lastError: string | null
  /** Whether the entry can still be retried. */
  status: QueueEntryStatus
}

/** The outcome of a single sync attempt. */
export type SyncResult =
  /** The server accepted the inspection. */
  | { status: 'synced'; entry: QueuedInspection }
  /** The server rejected the payload; retrying will not help. */
  | { status: 'rejected'; entry: QueuedInspection; error: string }
  /** The network is unreachable; the entry stays queued. */
  | { status: 'offline'; entry: QueuedInspection; error: string }

/** The outcome of draining the whole queue. */
export interface SyncSummary {
  /** Number of entries accepted by the server. */
  synced: number
  /** Number of entries the server rejected permanently. */
  rejected: number
  /** Number of entries that could not be sent because the network is down. */
  offline: number
}
