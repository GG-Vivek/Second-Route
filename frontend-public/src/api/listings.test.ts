import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getListings, getListing } from '@/api/listings'
import { api } from '@/api/client'

vi.mock('@/api/client', () => ({
  api: { get: vi.fn() },
}))

const mockGet = vi.mocked(api.get)

describe('the listings the storefront reads', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('asks for the public listings', async () => {
    mockGet.mockResolvedValue({ data: { items: [], total: 0, limit: 24, offset: 0, families: [], synthetic: false } })

    await getListings()
    expect(mockGet).toHaveBeenCalledWith('/public/listings', { params: {} })
  })

  it('passes the filter on', async () => {
    mockGet.mockResolvedValue({ data: { items: [], total: 0, limit: 24, offset: 0, families: [], synthetic: false } })

    await getListings({ family: 'MacBook Pro', search: 'M3', limit: 12, offset: 24 })
    expect(mockGet).toHaveBeenCalledWith('/public/listings', {
      params: { family: 'MacBook Pro', search: 'M3', limit: 12, offset: 24 },
    })
  })

  it('asks for one device by its identifier', async () => {
    mockGet.mockResolvedValue({ data: { id: 'abc' } })

    await getListing('abc')
    expect(mockGet).toHaveBeenCalledWith('/public/listings/abc')
  })
})
