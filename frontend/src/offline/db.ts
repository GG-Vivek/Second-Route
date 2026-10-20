/**
 * IndexedDB schema for the offline inspection store (F5.5).
 *
 * One database holds two object stores:
 *
 * - `drafts`: in-progress inspection forms, keyed by their client id, with
 *   an index on `unitId` so a unit's draft can be found without scanning.
 * - `queue`: completed inspections waiting for the network, keyed by their
 *   client id, with an index on `createdAt` so the queue can be drained in
 *   the order the inspections were completed.
 *
 * The database is opened lazily and cached, so callers never pay for it
 * until they actually touch the offline store.
 */

import { openDB, type DBSchema, type IDBPDatabase } from 'idb'
import type { InspectionDraft, QueuedInspection } from './types'

export const OFFLINE_DB_NAME = 'secondroute-offline'
export const OFFLINE_DB_VERSION = 1
export const DRAFT_STORE = 'drafts'
export const QUEUE_STORE = 'queue'

interface OfflineSchema extends DBSchema {
  drafts: {
    key: string
    value: InspectionDraft
    indexes: { 'by-unit': string }
  }
  queue: {
    key: string
    value: QueuedInspection
    indexes: { 'by-created': string }
  }
}

export type OfflineDatabase = IDBPDatabase<OfflineSchema>

let dbPromise: Promise<OfflineDatabase> | null = null

/**
 * Open (or reuse) the offline database.
 *
 * Opening is idempotent and the resulting promise is cached, so concurrent
 * callers share one connection.
 */
export function getOfflineDb(): Promise<OfflineDatabase> {
  if (dbPromise === null) {
    dbPromise = openDB<OfflineSchema>(OFFLINE_DB_NAME, OFFLINE_DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(DRAFT_STORE)) {
          const drafts = db.createObjectStore(DRAFT_STORE, { keyPath: 'id' })
          drafts.createIndex('by-unit', 'unitId')
        }
        if (!db.objectStoreNames.contains(QUEUE_STORE)) {
          const queue = db.createObjectStore(QUEUE_STORE, { keyPath: 'id' })
          queue.createIndex('by-created', 'createdAt')
        }
      },
    })
  }
  return dbPromise
}

/**
 * Drop the cached database handle.
 *
 * Used by tests to start from a clean slate, and after a schema change
 * during development.
 */
export function resetOfflineDb(): void {
  dbPromise = null
}
