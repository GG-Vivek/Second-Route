/**
 * Backtest API client (F5.6).
 */

import { api } from '@/api/client'

/** A point estimate with a bootstrap interval around it. */
export interface ConfidenceInterval {
  point_estimate: number
  lower: number
  upper: number
  confidence: number
  method: string
  samples: number
  seed: number
  n: number
  excludes_zero: boolean
}

/** A decision that was left out of the comparison, and why. */
export interface SkippedDecision {
  decision_id: string
  reason: string
}

/** One problem found in a decision's provenance. */
export interface LookAheadFinding {
  decision_id: string
  kind: string
  field: string
  as_of: string | null
  decision_time: string
  detail: string
}

/** The result of the look-ahead check. */
export interface LookAheadReport {
  has_leak: boolean
  is_clean: boolean
  finding_count: number
  findings: LookAheadFinding[]
}

/** The outcome of a backtest. */
export interface BacktestReport {
  baseline_name: string
  baseline_description: string
  baseline_channel: string | null
  decision_count: number
  skipped: SkippedDecision[]
  mean_engine_net: number | null
  mean_baseline_net: number | null
  mean_difference: number | null
  interval: ConfidenceInterval | null
  confidence: number
  method: string
  win_rate: number | null
  channel_breakdown: Record<string, Record<string, number>>
  lookahead: LookAheadReport | null
  window_start: string | null
  window_end: string | null
  warnings: string[]
}

/** A stored backtest run. */
export interface BacktestRun {
  id: string
  org_id: string | null
  created_at: string
  name: string
  baseline_name: string
  baseline_channel: string | null
  window_start: string | null
  window_end: string | null
  decision_count: number
  mean_difference: number | null
  ci_lower: number | null
  ci_upper: number | null
  confidence: number
  method: string
  samples: number
  seed: number
  is_synthetic: boolean
  report: BacktestReport
}

/** What to compare and over which window. */
export interface CreateBacktestRequest {
  org_id: string
  name?: string
  baseline?: 'fixed-channel' | 'most-common-channel'
  baseline_channel?: string | null
  window_start?: string | null
  window_end?: string | null
  confidence?: number
  samples?: number
  seed?: number
}

/** Run a backtest over the decisions of one organisation. */
export async function createBacktest(data: CreateBacktestRequest): Promise<BacktestRun> {
  return api.post<BacktestRun>('/backtests', data)
}

/** List the stored backtest runs, newest first. */
export async function listBacktests(orgId?: string): Promise<BacktestRun[]> {
  const params = orgId ? `?org_id=${encodeURIComponent(orgId)}` : ''
  return api.get<BacktestRun[]>(`/backtests${params}`)
}

/** Read one stored backtest run. */
export async function getBacktest(id: string): Promise<BacktestRun> {
  return api.get<BacktestRun>(`/backtests/${id}`)
}
