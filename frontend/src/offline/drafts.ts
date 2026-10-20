/**
 * Draft storage for in-progress inspections (F5.5).
 *
 * A draft is written on every meaningful form change, so a forced
 * disconnect, a crash, or a browser restart never loses the inspector's
 * work. Drafts are removed once the inspection has been accepted by the
 * server.
 */

import { DRAFT_STORE, getOfflineDb } from './db'
import type { InspectionDraft, InspectionFormValues } from './types'

/**
 * Return the draft for a unit, if there is one.
 */
export async function getDraft(unitId: string): Promise<InspectionDraft | undefined> {
  const db = await getOfflineDb()
  return db.getFromIndex(DRAFT_STORE, 'by-unit', unitId)
}

/**
 * Return every stored draft, newest save first.
 */
export async function listDrafts(): Promise<InspectionDraft[]> {
  const db = await getOfflineDb()
  const drafts = await db.getAll(DRAFT_STORE)
  return drafts.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
}

/**
 * Save the draft for a unit.
 *
 * Saving again for the same unit replaces the previous draft rather than
 * accumulating one draft per keystroke, so the store holds at most one
 * draft per unit.
 */
export async function saveDraft(
  unitId: string,
  values: InspectionFormValues,
  id?: string
): Promise<InspectionDraft> {
  const db = await getOfflineDb()
  const existing = id ? await db.get(DRAFT_STORE, id) : await getDraft(unitId)

  const draft: InspectionDraft = {
    id: existing?.id ?? crypto.randomUUID(),
    unitId,
    values,
    updatedAt: new Date().toISOString(),
  }

  await db.put(DRAFT_STORE, draft)
  return draft
}

/**
 * Remove the draft for a unit, if there is one.
 */
export async function deleteDraft(unitId: string): Promise<void> {
  const db = await getOfflineDb()
  const draft = await getDraft(unitId)
  if (draft) {
    await db.delete(DRAFT_STORE, draft.id)
  }
}

/**
 * Remove every draft.
 */
export async function clearDrafts(): Promise<void> {
  const db = await getOfflineDb()
  await db.clear(DRAFT_STORE)
}
