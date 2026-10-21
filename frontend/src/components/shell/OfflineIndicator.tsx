import { CloudUpload, WifiOff } from 'lucide-react'
import { useOffline } from '@/offline'
import { cn } from '@/utils/cn'
import { Tooltip } from '@/components/ui'

/**
 * The offline state.
 *
 * It lives in the shell rather than only on the inspection form, because an
 * operator who has lost the network needs to know before they start filling
 * in a form, not after.
 */
export function OfflineIndicator({ className }: { className?: string }) {
  const { isOnline, pendingCount, syncing } = useOffline()

  if (isOnline && pendingCount === 0 && !syncing) return null

  if (!isOnline) {
    return (
      <Tooltip
        content={
          pendingCount > 0
            ? `Offline. ${pendingCount} inspection(s) are waiting to sync.`
            : 'Offline. Your work is saved on this device.'
        }
      >
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-3xl bg-warning-container px-2.5 py-1',
            'text-xs font-medium text-on-warning-container',
            className
          )}
          data-testid="offline-indicator"
        >
          <WifiOff className="size-3" aria-hidden="true" />
          Offline
        </span>
      </Tooltip>
    )
  }

  return (
    <Tooltip
      content={
        syncing
          ? 'Syncing the queued inspections'
          : `${pendingCount} inspection(s) waiting to sync`
      }
    >
      <span
        className={cn(
          'inline-flex items-center gap-1.5 rounded-3xl bg-muted px-2.5 py-1',
          'text-xs font-medium text-muted-foreground',
          className
        )}
        data-testid="sync-indicator"
      >
        <CloudUpload className="size-3" aria-hidden="true" />
        {syncing ? 'Syncing' : `${pendingCount} queued`}
      </span>
    </Tooltip>
  )
}
