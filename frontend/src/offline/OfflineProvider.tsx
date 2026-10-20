/**
 * The offline sync provider (F5.5).
 *
 * Owns the state that the rest of the app needs to know about offline
 * work: whether the browser is online, how many inspections are waiting
 * in the queue, and whether a sync is currently running.
 *
 * The queue is drained when connectivity returns, when the app starts, and
 * whenever the user asks for it.
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { OfflineContext, type OfflineContextValue } from './OfflineContext'
import { queueSize, syncQueue, type InspectionSender } from './queue'
import { useOnlineStatus } from './useOnlineStatus'

export interface OfflineProviderProps {
  children: ReactNode
  /** Overrides the delivery function. Used by tests. */
  send?: InspectionSender
  /** Skips the automatic sync on mount. Used by tests. */
  autoSync?: boolean
}

export function OfflineProvider({ children, send, autoSync = true }: OfflineProviderProps) {
  const isOnline = useOnlineStatus()
  const [pendingCount, setPendingCount] = useState(0)
  const [syncing, setSyncing] = useState(false)
  const [lastSyncError, setLastSyncError] = useState<string | null>(null)

  const refreshPendingCount = useCallback(async () => {
    try {
      setPendingCount(await queueSize())
    } catch {
      // A storage failure must not break the app; the count is advisory.
      setPendingCount(0)
    }
  }, [])

  const sync = useCallback(async () => {
    setSyncing(true)
    try {
      const summary = await syncQueue(send)
      setLastSyncError(
        summary.rejected > 0 ? `${summary.rejected} queued inspection(s) were rejected` : null
      )
    } catch (error: unknown) {
      setLastSyncError(error instanceof Error ? error.message : 'Sync failed')
    } finally {
      setSyncing(false)
      await refreshPendingCount()
    }
  }, [send, refreshPendingCount])

  // Recount whenever the queue may have changed.
  useEffect(() => {
    void refreshPendingCount()
  }, [refreshPendingCount])

  // Drain the queue when connectivity returns.
  useEffect(() => {
    if (isOnline && autoSync) {
      void sync()
    }
  }, [isOnline, autoSync, sync])

  const value = useMemo<OfflineContextValue>(
    () => ({
      isOnline,
      pendingCount,
      syncing,
      lastSyncError,
      sync,
      refreshPendingCount,
    }),
    [isOnline, pendingCount, syncing, lastSyncError, sync, refreshPendingCount]
  )

  return <OfflineContext.Provider value={value}>{children}</OfflineContext.Provider>
}
