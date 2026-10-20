/**
 * Access to the offline state (F5.5).
 *
 * Kept in its own module so the provider file only exports components,
 * which keeps React Fast Refresh working in development.
 */

import { useContext } from 'react'
import { OfflineContext, type OfflineContextValue } from './OfflineContext'

/**
 * Read the offline state.
 *
 * Throws when used outside an `OfflineProvider`, because a component that
 * depends on the queue must be able to rely on the queue being tracked.
 */
export function useOffline(): OfflineContextValue {
  const context = useContext(OfflineContext)
  if (context === null) {
    throw new Error('useOffline must be used within an OfflineProvider')
  }
  return context
}
