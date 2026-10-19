import { api } from '@/api/client'
import type {
  SKU,
  SerialPrefixLookupResponse,
  Unit,
  UnitDetail,
  Inspection,
  Photo,
  CreateUnitRequest,
  CreateInspectionRequest,
  CreatePhotoRequest,
  UpdateUnitStatusRequest,
  ReturnReasonCode,
  OrderChannel,
  UnitStatus,
} from '@/types/intake'

// Re-export types for consumers
export type {
  SKU,
  SerialPrefixLookupResponse,
  Unit,
  UnitDetail,
  Inspection,
  Photo,
  CreateUnitRequest,
  CreateInspectionRequest,
  CreatePhotoRequest,
  UpdateUnitStatusRequest,
  ReturnReasonCode,
  OrderChannel,
  UnitStatus,
}

// SKU API
export async function listSKUs(params?: { family?: string; limit?: number; offset?: number }): Promise<SKU[]> {
  const searchParams = new URLSearchParams()
  if (params?.family) searchParams.set('family', params.family)
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.offset) searchParams.set('offset', String(params.offset))
  return api.get<SKU[]>(`/skus?${searchParams.toString()}`)
}

export async function getSKU(id: string): Promise<SKU> {
  return api.get<SKU>(`/skus/${id}`)
}

export async function lookupSKUBySerial(serial: string): Promise<SerialPrefixLookupResponse> {
  return api.get<SerialPrefixLookupResponse>(`/skus/lookup/serial?serial=${encodeURIComponent(serial)}`)
}

// Unit API
export async function createUnit(data: CreateUnitRequest): Promise<Unit> {
  return api.post<Unit>('/units', data)
}

export async function listUnits(params?: {
  status?: UnitStatus
  sku_id?: string
  limit?: number
  offset?: number
}): Promise<Unit[]> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.sku_id) searchParams.set('sku_id', params.sku_id)
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.offset) searchParams.set('offset', String(params.offset))
  return api.get<Unit[]>(`/units?${searchParams.toString()}`)
}

export async function getUnit(id: string): Promise<UnitDetail> {
  return api.get<UnitDetail>(`/units/${id}`)
}

export async function updateUnitStatus(id: string, data: UpdateUnitStatusRequest): Promise<Unit> {
  return api.patch<Unit>(`/units/${id}/status`, data)
}

// Inspection API
export async function createInspection(unitId: string, data: CreateInspectionRequest): Promise<Inspection> {
  return api.post<Inspection>(`/units/${unitId}/inspections`, data)
}

export async function listInspections(unitId: string): Promise<Inspection[]> {
  return api.get<Inspection[]>(`/units/${unitId}/inspections`)
}

// Photo API
export async function createPhoto(unitId: string, data: CreatePhotoRequest): Promise<Photo> {
  return api.post<Photo>(`/units/${unitId}/photos`, data)
}

export async function listPhotos(unitId: string): Promise<Photo[]> {
  return api.get<Photo[]>(`/units/${unitId}/photos`)
}

// Constants for forms
export const RETURN_REASON_CODES: { value: ReturnReasonCode; label: string }[] = [
  { value: 'buyer_remorse', label: 'Buyer Remorse' },
  { value: 'wrong_item', label: 'Wrong Item' },
  { value: 'damaged_in_shipping', label: 'Damaged in Shipping' },
  { value: 'defective', label: 'Defective' },
  { value: 'not_as_described', label: 'Not as Described' },
  { value: 'changed_mind', label: 'Changed Mind' },
  { value: 'better_price_found', label: 'Better Price Found' },
  { value: 'no_longer_needed', label: 'No Longer Needed' },
  { value: 'other', label: 'Other' },
]

export const ORDER_CHANNELS: { value: OrderChannel; label: string }[] = [
  { value: 'online', label: 'Online' },
  { value: 'retail', label: 'Retail' },
  { value: 'b2b', label: 'B2B' },
  { value: 'marketplace', label: 'Marketplace' },
  { value: 'other', label: 'Other' },
]

export const COSMETIC_GRADES = ['A', 'B', 'C', 'D']

export const ACTIVATION_LOCK_OPTIONS: { value: 'none' | 'present' | 'unknown'; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'present', label: 'Present' },
  { value: 'unknown', label: 'Unknown' },
]

export const UNIT_STATUSES: { value: UnitStatus; label: string }[] = [
  { value: 'received', label: 'Received' },
  { value: 'inspected', label: 'Inspected' },
  { value: 'decided', label: 'Decided' },
  { value: 'dispatched', label: 'Dispatched' },
  { value: 'sold', label: 'Sold' },
  { value: 'recycled', label: 'Recycled' },
  { value: 'donated', label: 'Donated' },
]

export const FUNCTIONAL_TESTS = [
  { key: 'display', label: 'Display' },
  { key: 'keyboard', label: 'Keyboard/Trackpad' },
  { key: 'ports', label: 'Ports' },
  { key: 'camera', label: 'Camera' },
  { key: 'audio', label: 'Audio' },
  { key: 'wifi', label: 'WiFi/Bluetooth' },
  { key: 'battery', label: 'Battery Charging' },
  { key: 'boot', label: 'Boots to OS' },
]

export const ACCESSORIES = [
  { key: 'charger', label: 'Charger' },
  { key: 'cable', label: 'Cable' },
  { key: 'box', label: 'Original Box' },
  { key: 'manual', label: 'Manual' },
  { key: 'other', label: 'Other Accessories' },
]

export function gradeColor(grade: string): string {
  switch (grade) {
    case 'A':
      return 'bg-green-100 text-green-800'
    case 'B':
      return 'bg-blue-100 text-blue-800'
    case 'C':
      return 'bg-yellow-100 text-yellow-800'
    case 'D':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-muted text-muted-foreground'
  }
}

export function lockColor(lock: string): string {
  switch (lock) {
    case 'none':
      return 'bg-green-100 text-green-800'
    case 'present':
      return 'bg-red-100 text-red-800'
    case 'unknown':
      return 'bg-yellow-100 text-yellow-800'
    default:
      return 'bg-muted text-muted-foreground'
  }
}