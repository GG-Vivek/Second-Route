import { api, rootApi } from '@/api/client'

/**
 * The state of one dependency.
 *
 * `not_configured` means the deployment does not use it. It is not the
 * same as `failed`, and the application is not degraded by it.
 */
export type DependencyState = 'ok' | 'failed' | 'not_configured'

export interface HealthChecks {
  database: DependencyState
  redis: DependencyState
}

export interface HealthResponse {
  status: 'healthy' | 'degraded'
  version: string
  environment: string
  checks: HealthChecks
}

/**
 * Ask whether the service is up.
 *
 * The health endpoint is at the root of the service rather than under
 * the versioned API prefix, so it is asked for through the root client.
 */
export async function getHealth(): Promise<HealthResponse> {
  const response = await rootApi.get<HealthResponse>('/health')
  return response.data
}

/** The status of one data source. */
export interface SourceStatus {
  source: string
  kind: string
  status: 'fresh' | 'stale' | 'missing'
  last_update: string | null
  age_hours: number | null
  error_count: number
  is_synthetic: boolean
  stale_limit_hours: number
}

/**
 * Ask about every data source.
 *
 * A source that is stale is not broken, but the confidence of every
 * decision that leans on it is reduced, and the operator should be able
 * to see that.
 */
export async function getSourceHealth(): Promise<SourceStatus[]> {
  return api.get<SourceStatus[]>('/sources/health')
}
