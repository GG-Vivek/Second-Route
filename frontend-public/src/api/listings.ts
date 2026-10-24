/**
 * The listings the storefront reads (Phase 10, extended in F11.2).
 */

import { api } from '@/api/client'

/** What a device is being offered at. */
export interface ListingPrice {
  amount: number
  currency: string
  /** Where the price came from. ``synthetic`` means it was modelled. */
  source: string
  /** When the price was current, as an ISO timestamp. */
  as_of: string | null
  /** True when the price is a modelled expectation. */
  is_estimate: boolean
}

/** One photograph of a device. */
export interface ListingPhoto {
  url: string
  alt: string
}

/** One device, for sale. */
export interface Listing {
  id: string
  title: string
  /** The kind of device: laptop, phone, tv, refrigerator and so on. */
  category: string
  /** The kind of device, in words a buyer uses. */
  category_label: string
  /** One line about the device, written for the card. */
  summary: string
  family: string
  model_name: string
  year: string
  storage_gb: string
  ram_gb: string
  color: string
  /** The cosmetic grade, A to D. */
  grade: string
  /** The grade in words a buyer understands. */
  condition: string
  /** Null for a device that has no battery, such as a refrigerator. */
  battery_health_pct: string | null
  price: ListingPrice
  photo: ListingPhoto | null
  photo_count: number
  listed_at: string
  in_stock: boolean
}

/** One functional test. */
export interface ListingCheck {
  name: string
  passed: boolean
}

/** One device, in full. */
export interface ListingDetail extends Listing {
  photos: ListingPhoto[]
  accessories: string[]
  checks: ListingCheck[]
  highlights: string[]
}

/** One kind of device on sale, with how many there are. */
export interface ListingCategory {
  key: string
  label: string
  count: number
}

/** A page of devices. */
export interface ListingPage {
  items: Listing[]
  total: number
  limit: number
  offset: number
  /** The families on sale. */
  families: string[]
  /** The kinds of device on sale, for the filter. */
  categories: ListingCategory[]
  /** True when the prices on the page are modelled rather than observed. */
  synthetic: boolean
}

/** What to ask for. */
export interface ListingQuery {
  family?: string
  category?: string
  search?: string
  limit?: number
  offset?: number
}

/**
 * The devices that are on sale.
 *
 * @param query - What to narrow it by.
 * @returns A page of listings.
 */
export async function getListings(query: ListingQuery = {}): Promise<ListingPage> {
  const response = await api.get<ListingPage>('/public/listings', { params: query })
  return response.data
}

/**
 * One device, in full.
 *
 * @param id - The identifier of the listing.
 * @returns The listing.
 */
export async function getListing(id: string): Promise<ListingDetail> {
  const response = await api.get<ListingDetail>(`/public/listings/${id}`)
  return response.data
}
