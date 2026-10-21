import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getHealth, getSourceHealth } from '@/api/health'
import { api } from '@/api/client'

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
  },
}))

const mockGet = vi.mocked(api.get)

/**
 * The shape of the health responses.
 *
 * The endpoint answers with an object: the sources and a summary of them.
 * An earlier version of the front end expected a list and asked for
 * ``.map`` on an object, which took the whole page down.
 */
describe('the health API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('asks the versioned path, so that the page of its own is not shadowed', async () => {
    mockGet.mockResolvedValue({
      status: 'healthy',
      version: '0.1.0',
      environment: 'test',
      checks: { database: 'ok', redis: 'ok' },
    })

    await getHealth()
    expect(mockGet).toHaveBeenCalledWith('/health')
  })

  it('reads the sources out of the object the endpoint answers with', async () => {
    mockGet.mockResolvedValue({
      sources: [
        {
          source: 'synthetic',
          kind: 'price',
          status: 'fresh',
          last_update: '2026-10-21T09:00:00Z',
          age_hours: 1,
          error_count: 0,
          is_synthetic: true,
          stale_limit_hours: 48,
        },
      ],
      summary: { total: 1, fresh: 1, stale: 0, missing: 0, errors: 0 },
      stale_limit_hours: 48,
    })

    const health = await getSourceHealth()
    expect(Array.isArray(health.sources)).toBe(true)
    expect(health.sources).toHaveLength(1)
    expect(health.sources[0].source).toBe('synthetic')
    expect(health.summary.total).toBe(1)
  })

  it('reports a dependency that is not in use as such', async () => {
    mockGet.mockResolvedValue({
      status: 'healthy',
      version: '0.1.0',
      environment: 'test',
      checks: { database: 'ok', redis: 'not_configured' },
    })

    const health = await getHealth()
    expect(health.checks.redis).toBe('not_configured')
  })
})
