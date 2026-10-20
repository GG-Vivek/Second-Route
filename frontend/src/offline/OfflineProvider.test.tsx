/**
 * Tests for the offline sync provider (F5.5).
 */

import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { OfflineProvider } from '@/offline/OfflineProvider'
import { useOffline } from '@/offline/useOffline'
import { clearDrafts } from '@/offline/drafts'
import { clearQueue, enqueueInspection, queueSize } from '@/offline/queue'
import { resetOfflineDb } from '@/offline/db'
import type { CreateInspectionRequest } from '@/types/intake'

const PAYLOAD: CreateInspectionRequest = {
  battery_health_pct: '95',
  battery_cycles: '120',
  cosmetic_grade: 'A',
  functional_tests_json: { display: true },
  activation_lock: 'none',
  accessories_json: { charger: true },
  notes: 'offline',
  offline_created: true,
}

/** Sets `navigator.onLine` and fires the matching window event. */
function setOnline(online: boolean) {
  Object.defineProperty(window.navigator, 'onLine', {
    configurable: true,
    get: () => online,
  })
  act(() => {
    window.dispatchEvent(new Event(online ? 'online' : 'offline'))
  })
}

function StatusProbe() {
  const { isOnline, pendingCount, syncing, sync } = useOffline()
  return (
    <div>
      <span data-testid="online">{String(isOnline)}</span>
      <span data-testid="pending">{pendingCount}</span>
      <span data-testid="syncing">{String(syncing)}</span>
      <button onClick={() => void sync()}>Sync now</button>
    </div>
  )
}

describe('OfflineProvider', () => {
  beforeEach(async () => {
    await clearDrafts()
    await clearQueue()
    resetOfflineDb()
    setOnline(true)
  })

  it('reports the browser connectivity', async () => {
    setOnline(false)

    render(
      <MemoryRouter>
        <OfflineProvider autoSync={false}>
          <StatusProbe />
        </OfflineProvider>
      </MemoryRouter>
    )

    expect(screen.getByTestId('online')).toHaveTextContent('false')
  })

  it('counts the queued inspections', async () => {
    await enqueueInspection('unit-1', PAYLOAD)
    await enqueueInspection('unit-2', PAYLOAD)

    render(
      <MemoryRouter>
        <OfflineProvider autoSync={false}>
          <StatusProbe />
        </OfflineProvider>
      </MemoryRouter>
    )

    await waitFor(() => expect(screen.getByTestId('pending')).toHaveTextContent('2'))
  })

  it('drains the queue when the sync button is pressed', async () => {
    await enqueueInspection('unit-1', PAYLOAD)
    const send = vi.fn().mockResolvedValue(undefined)

    render(
      <MemoryRouter>
        <OfflineProvider autoSync={false} send={send}>
          <StatusProbe />
        </OfflineProvider>
      </MemoryRouter>
    )

    await waitFor(() => expect(screen.getByTestId('pending')).toHaveTextContent('1'))
    await userEvent.click(screen.getByRole('button', { name: 'Sync now' }))

    await waitFor(() => expect(send).toHaveBeenCalledTimes(1))
    await waitFor(async () => expect(await queueSize()).toBe(0))
  })

  it('syncs automatically when the connection returns', async () => {
    setOnline(false)
    await enqueueInspection('unit-1', PAYLOAD)
    const send = vi.fn().mockResolvedValue(undefined)

    render(
      <MemoryRouter>
        <OfflineProvider send={send}>
          <StatusProbe />
        </OfflineProvider>
      </MemoryRouter>
    )

    expect(send).not.toHaveBeenCalled()

    setOnline(true)

    await waitFor(() => expect(send).toHaveBeenCalledTimes(1))
  })

  it('throws when useOffline is used outside a provider', () => {
    // React logs the error; silence it for this expected failure.
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => render(<StatusProbe />)).toThrow(/OfflineProvider/)

    consoleError.mockRestore()
  })
})
