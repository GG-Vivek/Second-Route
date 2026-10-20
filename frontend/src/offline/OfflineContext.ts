/**
 * The offline context (F5.5).
 *
 * Separate from the provider so that the context object and the hook that
 * reads it can live in modules that export no components. React Fast
 * Refresh only rewrites a module when it exports components exclusively.
 */

import { createContext } from 'react'

export interface OfflineContextValue {
  /** Whether the browser believes it is online. */
  isOnline: boolean
  /** How many inspections are waiting to be sent. */
  pendingCount: number
  /** Whether a sync is currently running. */
  syncing: boolean
  /** The last error raised by a sync attempt, or `null`. */
  lastSyncError: string | null
  /** Drain the queue now. */
  sync: () => Promise<void>
  /** Recount the queue. */
  refreshPendingCount: () => Promise<void>
}

export const OfflineContext = createContext<OfflineContextValue | null>(null)
