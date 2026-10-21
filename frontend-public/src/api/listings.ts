/**
 * The listings the storefront reads (Phase 10).
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

/** A page of devices. */
export interface ListingPage {
  items: Listing[]
  total: number
  limit: number
  offset: number
  /** The families on sale, for the filter. */
  families: string[]
  /** True when the prices on the page are modelled rather than observed. */
  synthetic: boolean
}

/** What to ask for. */
export interface ListingQuery {
  family?: string
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
