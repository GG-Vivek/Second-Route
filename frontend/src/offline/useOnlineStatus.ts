/**
 * Online/offline detection (F5.5).
 *
 * The browser reports connectivity through `navigator.onLine` and fires
 * `online`/`offline` events when it changes. The hook wraps that in React
 * state so components can react to it.
 */

import { useEffect, useState } from 'react'

/**
 * Return whether the browser currently believes it is online.
 */
export function useOnlineStatus(): boolean {
  const [isOnline, setIsOnline] = useState<boolean>(() =>
    typeof navigator === 'undefined' ? true : navigator.onLine
  )

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // Re-read on mount: the browser may have changed state between the
    // initial render and the effect running.
    setIsOnline(navigator.onLine)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return isOnline
}
