// Type definitions for the intake module

export interface SKU {
  id: string
  family: string
  model_name: string
  year: string
  storage_gb: string
  ram_gb: string
  color: string
  region: string
  specs_json: Record<string, unknown>
  source: string
  as_of: string
}

export interface SerialPrefixLookupResponse {
  sku: SKU
  matched_prefix: string
}

export type ReturnReasonCode =
  | 'buyer_remorse'
  | 'wrong_item'
  | 'damaged_in_shipping'
  | 'defective'
  | 'not_as_described'
  | 'changed_mind'
  | 'better_price_found'
  | 'no_longer_needed'
  | 'other'

export type OrderChannel = 'online' | 'retail' | 'b2b' | 'marketplace' | 'other'

export type UnitStatus =
  | 'received'
  | 'inspected'
  | 'decided'
  | 'dispatched'
  | 'sold'
  | 'recycled'
  | 'donated'

export interface Unit {
  id: string
  org_id: string | null
  sku_id: string
  serial: string | null
  received_at: string
  return_reason_code: ReturnReasonCode
  order_channel: OrderChannel
  status: UnitStatus
  sku?: SKU
}

export interface Inspection {
  id: string
  unit_id: string
  inspector_id: string | null
  created_at: string
  battery_health_pct: string
  battery_cycles: string | null
  cosmetic_grade: string
  functional_tests_json: Record<string, boolean>
  activation_lock: 'none' | 'present' | 'unknown'
  accessories_json: Record<string, boolean>
  notes: string | null
  /** True when the inspection was created offline and synced later. */
  offline_created: boolean
}

export interface Photo {
  id: string
  unit_id: string
  inspection_id: string
  storage_path: string
  exif_stripped: boolean
  created_at: string
}

export interface UnitDetail extends Unit {
  inspections: Inspection[]
  photos: Photo[]
}

export interface CreateUnitRequest {
  sku_id: string
  serial?: string
  return_reason_code: ReturnReasonCode
  order_channel: OrderChannel
}

export interface CreateInspectionRequest {
  battery_health_pct: string
  battery_cycles?: string
  cosmetic_grade: string
  functional_tests_json: Record<string, boolean>
  activation_lock: 'none' | 'present' | 'unknown'
  accessories_json: Record<string, boolean>
  notes?: string
  /** True when the inspection was completed offline and is being synced. */
  offline_created?: boolean
}

export interface CreatePhotoRequest {
  inspection_id: string
  storage_path: string
  exif_stripped: boolean
}

export interface UpdateUnitStatusRequest {
  status: UnitStatus
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface ApiError {
  error: string
  message: string
  serial?: string
  detail?: string | Array<{ msg: string; loc: string[] }>
}