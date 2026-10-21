import { api } from '@/api/client'

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
 * The health endpoint answers at the root of the service as well, because
 * that is where a load balancer and a container health check look. The
 * application asks for the versioned one: the root path belongs to the
 * infrastructure, and the front end has a page of its own at ``/health``.
 */
export async function getHealth(): Promise<HealthResponse> {
  return api.get<HealthResponse>('/health')
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

/** How many sources are in each state. */
export interface SourceSummary {
  total: number
  fresh: number
  stale: number
  missing: number
  errors: number
}

/** The health of every data source, and a summary of it. */
export interface SourceHealth {
  sources: SourceStatus[]
  summary: SourceSummary
  stale_limit_hours: number
}

/**
 * Ask about every data source.
 *
 * A source that is stale is not broken, but the confidence of every
 * decision that leans on it is reduced, and the operator should be able
 * to see that.
 */
export async function getSourceHealth(): Promise<SourceHealth> {
  return api.get<SourceHealth>('/sources/health')
}
