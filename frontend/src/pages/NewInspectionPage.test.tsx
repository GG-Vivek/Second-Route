/**
 * The forced-disconnect acceptance test for offline inspection (F5.5).
 *
 * "A full inspection completed offline syncs correctly when the network
 * returns. No data lost in a forced-disconnect test."
 *
 * The test drives the real inspection form: it fills every field, cuts the
 * network, submits, and then restores the network and checks that the
 * inspection reaches the server with nothing lost on the way.
 */

import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NewInspectionPage } from './NewInspectionPage'
import { OfflineProvider } from '@/offline/OfflineProvider'
import { clearDrafts, getDraft } from '@/offline/drafts'
import { clearQueue, listQueue, queueSize } from '@/offline/queue'
import { resetOfflineDb } from '@/offline/db'

const getUnit = vi.fn()
const createInspection = vi.fn()

vi.mock('@/api/intake', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/intake')>()
  return {
    ...actual,
    getUnit: (...args: unknown[]) => getUnit(...args),
    createInspection: (...args: unknown[]) => createInspection(...args),
  }
})

const UNIT = {
  id: 'unit-1',
  org_id: 'org-1',
  sku_id: 'sku-1',
  serial: 'SERIAL123',
  received_at: '2026-10-20T00:00:00Z',
  return_reason_code: 'buyer_remorse' as const,
  order_channel: 'online' as const,
  status: 'received' as const,
  sku: {
    id: 'sku-1',
    family: 'MacBook Pro',
    model_name: 'M3 Pro',
    year: '2023',
    storage_gb: '512',
    ram_gb: '18',
    color: 'Space Gray',
    region: 'US',
    specs_json: {},
    source: 'test',
    as_of: '2024-01-15',
  },
  inspections: [],
  photos: [],
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

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/units/unit-1/inspection/new']}>
      <OfflineProvider>
        <Routes>
          <Route path="/units/:id/inspection/new" element={<NewInspectionPage />} />
          <Route path="/units/:id" element={<div>Unit detail</div>} />
        </Routes>
      </OfflineProvider>
    </MemoryRouter>
  )
}

/** Fill in every field of the inspection form. */
async function fillInspectionForm() {
  await userEvent.clear(screen.getByLabelText(/Battery Health/i))
  await userEvent.type(screen.getByLabelText(/Battery Health/i), '95')
  await userEvent.type(screen.getByLabelText(/Battery Cycles/i), '120')
  await userEvent.click(screen.getByRole('radio', { name: /Excellent/i }))
  await userEvent.click(screen.getByLabelText(/Display/i))
  await userEvent.click(screen.getByLabelText(/Charger/i))
  await userEvent.type(
    screen.getByPlaceholderText(/additional notes/i),
    'Full inspection completed offline'
  )
}

describe('offline inspection - forced disconnect', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await clearDrafts()
    await clearQueue()
    resetOfflineDb()
    getUnit.mockResolvedValue(UNIT)
    createInspection.mockResolvedValue({ id: 'inspection-1' })
    setOnline(true)
  })

  it('queues a completed inspection when the network is down', async () => {
    setOnline(false)
    renderPage()

    await screen.findByText('New Inspection')
    await fillInspectionForm()

    await userEvent.click(screen.getByRole('button', { name: /Save Offline/i }))

    await waitFor(async () => expect(await queueSize()).toBe(1))
    expect(createInspection).not.toHaveBeenCalled()
  })

  it('shows the inspector that the inspection was saved on the device', async () => {
    setOnline(false)
    renderPage()

    await screen.findByText('New Inspection')
    await fillInspectionForm()
    await userEvent.click(screen.getByRole('button', { name: /Save Offline/i }))

    expect(
      await screen.findByText(/Inspection saved on this device/i)
    ).toBeInTheDocument()
  })

  it('keeps every field of the queued inspection', async () => {
    setOnline(false)
    renderPage()

    await screen.findByText('New Inspection')
    await fillInspectionForm()
    await userEvent.click(screen.getByRole('button', { name: /Save Offline/i }))

    await waitFor(async () => expect(await queueSize()).toBe(1))

    const [entry] = await listQueue()
    expect(entry.unitId).toBe('unit-1')
    expect(entry.payload.battery_health_pct).toBe('95')
    expect(entry.payload.battery_cycles).toBe('120')
    expect(entry.payload.cosmetic_grade).toBe('A')
    expect(entry.payload.functional_tests_json.display).toBe(true)
    expect(entry.payload.accessories_json.charger).toBe(true)
    expect(entry.payload.notes).toBe('Full inspection completed offline')
    expect(entry.payload.offline_created).toBe(true)
  })

  it('syncs the queued inspection when the network returns', async () => {
    setOnline(false)
    renderPage()

    await screen.findByText('New Inspection')
    await fillInspectionForm()
    await userEvent.click(screen.getByRole('button', { name: /Save Offline/i }))
    await waitFor(async () => expect(await queueSize()).toBe(1))

    // The network comes back.
    setOnline(true)

    await waitFor(() => expect(createInspection).toHaveBeenCalledTimes(1))
    await waitFor(async () => expect(await queueSize()).toBe(0))

    const [unitId, payload] = createInspection.mock.calls[0]
    expect(unitId).toBe('unit-1')
    expect(payload).toMatchObject({
      battery_health_pct: '95',
      battery_cycles: '120',
      cosmetic_grade: 'A',
      notes: 'Full inspection completed offline',
    })
  })

  it('keeps the draft when the inspection is queued', async () => {
    setOnline(false)
    renderPage()

    await screen.findByText('New Inspection')
    await fillInspectionForm()
    await userEvent.click(screen.getByRole('button', { name: /Save Offline/i }))

    await waitFor(async () => {
      const draft = await getDraft('unit-1')
      expect(draft?.values.battery_health_pct).toBe('95')
      expect(draft?.values.notes).toBe('Full inspection completed offline')
    })
  })

  it('shows the offline banner while disconnected', async () => {
    setOnline(false)
    renderPage()

    expect(await screen.findByText(/You are offline/i)).toBeInTheDocument()
  })
})
