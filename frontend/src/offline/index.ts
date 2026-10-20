/**
 * Offline inspection support (F5.5).
 *
 * Re-exports the public surface of the offline module so callers import
 * from one place.
 */

export {
  DRAFT_STORE,
  OFFLINE_DB_NAME,
  OFFLINE_DB_VERSION,
  QUEUE_STORE,
  getOfflineDb,
  resetOfflineDb,
} from './db'
export {
  clearDrafts,
  deleteDraft,
  getDraft,
  listDrafts,
  saveDraft,
} from './drafts'
export {
  HttpStatusError,
  clearQueue,
  enqueueInspection,
  listQueue,
  queueSize,
  removeFromQueue,
  syncEntry,
  syncQueue,
  type InspectionSender,
} from './queue'
export { describeError, isNetworkError, submitInspection, type SubmitOutcome } from './submit'
export { OfflineProvider } from './OfflineProvider'
export { OfflineContext, type OfflineContextValue } from './OfflineContext'
export { useOffline } from './useOffline'
export { useOnlineStatus } from './useOnlineStatus'
export type {
  InspectionDraft,
  InspectionFormValues,
  QueuedInspection,
  QueueEntryStatus,
  SyncResult,
  SyncSummary,
} from './types'
