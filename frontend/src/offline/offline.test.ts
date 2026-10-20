/**
 * Tests for the offline draft store and submission queue (F5.5).
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { clearDrafts, deleteDraft, getDraft, listDrafts, saveDraft } from '@/offline/drafts'
import {
  clearQueue,
  enqueueInspection,
  HttpStatusError,
  listQueue,
  queueSize,
  removeFromQueue,
  syncEntry,
  syncQueue,
} from '@/offline/queue'
import { resetOfflineDb } from '@/offline/db'
import { submitInspection } from '@/offline/submit'
import type { InspectionFormValues } from '@/offline/types'
import type { CreateInspectionRequest } from '@/types/intake'

const VALUES: InspectionFormValues = {
  battery_health_pct: '95',
  battery_cycles: '120',
  cosmetic_grade: 'A',
  functional_tests_json: { display: true },
  activation_lock: 'none',
  accessories_json: { charger: true },
  notes: 'Looks good',
}

const PAYLOAD: CreateInspectionRequest = {
  battery_health_pct: '95',
  battery_cycles: '120',
  cosmetic_grade: 'A',
  functional_tests_json: { display: true },
  activation_lock: 'none',
  accessories_json: { charger: true },
  notes: 'Looks good',
  offline_created: true,
}

async function resetStore() {
  await clearDrafts()
  await clearQueue()
  resetOfflineDb()
}

describe('offline draft store', () => {
  beforeEach(resetStore)

  it('stores a draft for a unit', async () => {
    const draft = await saveDraft('unit-1', VALUES)

    expect(draft.unitId).toBe('unit-1')
    expect(draft.values).toEqual(VALUES)
    expect(draft.id).toBeTruthy()
  })

  it('reads back the draft for a unit', async () => {
    await saveDraft('unit-1', VALUES)

    const draft = await getDraft('unit-1')
    expect(draft?.values).toEqual(VALUES)
  })

  it('returns undefined for a unit with no draft', async () => {
    expect(await getDraft('missing')).toBeUndefined()
  })

  it('replaces the draft for a unit instead of accumulating them', async () => {
    await saveDraft('unit-1', VALUES)
    await saveDraft('unit-1', { ...VALUES, cosmetic_grade: 'B' })

    const drafts = await listDrafts()
    expect(drafts).toHaveLength(1)
    expect(drafts[0].values.cosmetic_grade).toBe('B')
  })

  it('keeps drafts for different units apart', async () => {
    await saveDraft('unit-1', VALUES)
    await saveDraft('unit-2', { ...VALUES, notes: 'other' })

    expect(await listDrafts()).toHaveLength(2)
    expect((await getDraft('unit-2'))?.values.notes).toBe('other')
  })

  it('deletes the draft for a unit', async () => {
    await saveDraft('unit-1', VALUES)
    await deleteDraft('unit-1')

    expect(await getDraft('unit-1')).toBeUndefined()
  })

  it('deleting a unit with no draft is a no-op', async () => {
    await expect(deleteDraft('missing')).resolves.toBeUndefined()
  })
})

describe('offline submission queue', () => {
  beforeEach(resetStore)

  it('enqueues an inspection with pending status', async () => {
    const entry = await enqueueInspection('unit-1', PAYLOAD)

    expect(entry.status).toBe('pending')
    expect(entry.attempts).toBe(0)
    expect(entry.lastError).toBeNull()
    expect(await queueSize()).toBe(1)
  })

  it('returns queue entries oldest first', async () => {
    const first = await enqueueInspection('unit-1', PAYLOAD)
    await enqueueInspection('unit-2', PAYLOAD)
    // Force a distinct ordering key.
    const db = await (await import('@/offline/db')).getOfflineDb()
    const stored = await db.get('queue', first.id)
    await db.put('queue', { ...stored!, createdAt: '2000-01-01T00:00:00.000Z' })

    const entries = await listQueue()
    expect(entries[0].unitId).toBe('unit-1')
  })

  it('removes a single entry from the queue', async () => {
    const entry = await enqueueInspection('unit-1', PAYLOAD)
    await removeFromQueue(entry.id)

    expect(await queueSize()).toBe(0)
  })
})

describe('queue sync', () => {
  beforeEach(resetStore)

  it('removes an entry once the server accepts it', async () => {
    await enqueueInspection('unit-1', PAYLOAD)
    const send = vi.fn().mockResolvedValue(undefined)

    const summary = await syncQueue(send)

    expect(summary.synced).toBe(1)
    expect(summary.rejected).toBe(0)
    expect(summary.offline).toBe(0)
    expect(await queueSize()).toBe(0)
  })

  it('keeps an entry queued when the network is down', async () => {
    await enqueueInspection('unit-1', PAYLOAD)
    const send = vi.fn().mockRejectedValue(new Error('Network Error'))

    const summary = await syncQueue(send)

    expect(summary.offline).toBe(1)
    expect(summary.synced).toBe(0)
    expect(await queueSize()).toBe(1)
  })

  it('records the attempt count and the error on a failed send', async () => {
    await enqueueInspection('unit-1', PAYLOAD)
    const send = vi.fn().mockRejectedValue(new Error('Network Error'))

    await syncQueue(send)

    const [entry] = await listQueue()
    expect(entry.attempts).toBe(1)
    expect(entry.lastError).toBe('Network Error')
    expect(entry.status).toBe('pending')
  })

  it('marks an entry as failed when the server rejects the payload', async () => {
    await enqueueInspection('unit-1', PAYLOAD)
    const send = vi.fn().mockRejectedValue(new HttpStatusError(422, 'Invalid payload'))

    const summary = await syncQueue(send)

    expect(summary.rejected).toBe(1)
    const [entry] = await listQueue()
    expect(entry.status).toBe('failed')
    expect(entry.lastError).toBe('Invalid payload')
  })

  it('retries a server error without giving up', async () => {
    await enqueueInspection('unit-1', PAYLOAD)
    const send = vi.fn().mockRejectedValue(new HttpStatusError(503, 'Service Unavailable'))

    const summary = await syncQueue(send)

    expect(summary.offline).toBe(1)
    const [entry] = await listQueue()
    expect(entry.status).toBe('pending')
  })

  it('syncs every queued entry', async () => {
    await enqueueInspection('unit-1', PAYLOAD)
    await enqueueInspection('unit-2', PAYLOAD)
    const send = vi.fn().mockResolvedValue(undefined)

    const summary = await syncQueue(send)

    expect(summary.synced).toBe(2)
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('sends the queued payload unchanged', async () => {
    await enqueueInspection('unit-1', PAYLOAD)
    const send = vi.fn().mockResolvedValue(undefined)

    await syncQueue(send)

    expect(send).toHaveBeenCalledWith('unit-1', PAYLOAD)
  })

  it('a rejected entry does not stop the rest of the queue', async () => {
    await enqueueInspection('unit-1', PAYLOAD)
    await enqueueInspection('unit-2', PAYLOAD)
    const send = vi
      .fn()
      .mockRejectedValueOnce(new HttpStatusError(422, 'Invalid payload'))
      .mockResolvedValueOnce(undefined)

    const summary = await syncQueue(send)

    expect(summary.rejected).toBe(1)
    expect(summary.synced).toBe(1)
    expect(await queueSize()).toBe(1)
  })

  it('syncEntry reports the outcome without touching the queue', async () => {
    const entry = await enqueueInspection('unit-1', PAYLOAD)
    const send = vi.fn().mockResolvedValue(undefined)

    const result = await syncEntry(entry, send)

    expect(result.status).toBe('synced')
    expect(await queueSize()).toBe(1)
  })
})

describe('submitInspection', () => {
  beforeEach(resetStore)

  it('submits directly when online', async () => {
    const send = vi.fn().mockResolvedValue(undefined)

    const outcome = await submitInspection('unit-1', PAYLOAD, true, send)

    expect(outcome.status).toBe('submitted')
    expect(await queueSize()).toBe(0)
  })

  it('queues the inspection when offline', async () => {
    const send = vi.fn().mockResolvedValue(undefined)

    const outcome = await submitInspection('unit-1', PAYLOAD, false, send)

    expect(outcome.status).toBe('queued')
    expect(send).not.toHaveBeenCalled()
    expect(await queueSize()).toBe(1)
  })

  it('queues the inspection when the network fails mid-request', async () => {
    const send = vi.fn().mockRejectedValue(new Error('Network Error'))

    const outcome = await submitInspection('unit-1', PAYLOAD, true, send)

    expect(outcome.status).toBe('queued')
    expect(await queueSize()).toBe(1)
  })

  it('reports a server rejection instead of queueing it', async () => {
    const error = Object.assign(new Error('Request failed'), {
      response: { status: 422, data: { detail: 'Invalid battery health' } },
    })
    const send = vi.fn().mockRejectedValue(error)

    const outcome = await submitInspection('unit-1', PAYLOAD, true, send)

    expect(outcome.status).toBe('rejected')
    expect(await queueSize()).toBe(0)
  })

  it('removes the draft once the inspection is accepted', async () => {
    await saveDraft('unit-1', VALUES)
    const send = vi.fn().mockResolvedValue(undefined)

    await submitInspection('unit-1', PAYLOAD, true, send)

    expect(await getDraft('unit-1')).toBeUndefined()
  })

  it('keeps the draft when the inspection is queued', async () => {
    await saveDraft('unit-1', VALUES)
    const send = vi.fn().mockResolvedValue(undefined)

    await submitInspection('unit-1', PAYLOAD, false, send)

    expect(await getDraft('unit-1')).toBeDefined()
  })
})
