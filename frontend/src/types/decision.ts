// Type definitions for the decision engine (Phase 2)

export type DispositionChannel =
  | 'RESELL_OPEN_BOX'
  | 'RESELL_REFURB'
  | 'PARTS_HARVEST'
  | 'RECYCLE'
  | 'DONATE'
  | 'HOLD'
  | 'SAFE_DEFAULT'

export type RiskProfile = 'conservative' | 'balanced' | 'aggressive'

export type Grade = 'A' | 'B' | 'C' | 'D'

export interface CostBreakdown {
  sale_price: number
  fees: number
  logistics: number
  handling: number
  repair: number
  holding: number
  total_cost: number
  net: number
}

export interface Candidate {
  channel: DispositionChannel
  eligible: boolean
  exclusion_reason: string | null
  mean: number
  stddev: number
  p10: number
  p50: number
  p90: number
  probability_best: number
  certainty_equivalent: number
  grade_probabilities: Record<Grade, number>
  price_sources: Record<string, string>
  price_as_of: Record<string, string>
  breakdown: CostBreakdown
}

export interface Reason {
  code: string
  label: string
  contribution: number
  favours_recommended: boolean
  text: string
}

export interface FlipCondition {
  input_name: string
  input_kind: 'numeric' | 'categorical'
  current_value: number | string
  threshold_value: number | string
  new_channel: DispositionChannel
  direction: string
  description: string
  target_channel: string | null
}

export interface ActionStep {
  order: number
  title: string
  detail: string
  reference: string | null
}

export interface DataFreshness {
  price_sources: Record<string, string>
  price_as_of: Record<string, string>
  cost_sources: Record<string, string>
  cost_as_of: Record<string, string>
  is_synthetic: boolean
  warnings: string[]
}

export interface Decision {
  id: string
  unit_id: string
  created_at: string
  model_version: string
  risk_profile: RiskProfile
  recommended_channel: DispositionChannel
  confidence: number
  fallback_used: boolean
  fallback_channel: string | null
  candidates: Candidate[]
  reasons: Reason[]
  flip_conditions: FlipCondition[]
  action_steps: ActionStep[]
  data_freshness: DataFreshness
  input_snapshot_hash: string
  is_prototype: boolean
  prototype_badge: string
}

export interface DecisionSummary {
  id: string
  unit_id: string
  created_at: string
  recommended_channel: DispositionChannel
  confidence: number
  fallback_used: boolean
  risk_profile: RiskProfile
}

export interface DecisionList {
  items: DecisionSummary[]
  total: number
  limit: number
  offset: number
}

export interface CreateDecisionRequest {
  risk_profile?: RiskProfile
  as_of?: string
}

export interface ReproducibilityResult {
  decision_id: string
  input_snapshot_hash: string
  replayed_hash: string
  matches: boolean
  recommended_channel: DispositionChannel
  confidence: number
  details: Record<string, unknown>
}

export interface Override {
  id: string
  decision_id: string
  user_id: string | null
  chosen_channel: string
  reason_text: string
  created_at: string
}

export interface OverrideList {
  items: Override[]
  total: number
  limit: number
  offset: number
}

export interface CreateOverrideRequest {
  chosen_channel: string
  reason_text: string
}

export interface Outcome {
  id: string
  unit_id: string
  decision_id: string
  channel_taken: string
  sale_price: number
  fees_actual: number
  repair_cost_actual: number
  logistics_actual: number
  days_to_disposition: number
  final_status: string
  recorded_at: string
  net: number
}

export interface OutcomeList {
  items: Outcome[]
  total: number
  limit: number
  offset: number
}

export interface CreateOutcomeRequest {
  channel_taken: string
  sale_price: number
  fees_actual: number
  repair_cost_actual: number
  logistics_actual: number
  days_to_disposition: number
  final_status: string
  decision_id?: string
}

export interface ChannelPrediction {
  channel: string
  p10: number
  p50: number
  p90: number
  mean: number
}

export interface PredictedVsRealized {
  unit_id: string
  decision_id: string
  outcome_id: string
  channel: string
  recommended_channel: string
  used_recommended: boolean
  predicted: ChannelPrediction
  realized_net: number
  residual: number
  absolute_residual: number
  in_range: boolean
  within_p10_p90: boolean
  below_p10: boolean
  above_p90: boolean
  recorded_at: string
}

export interface PredictedVsRealizedSummary {
  total: number
  in_range_count: number
  in_range_rate: number
  below_p10_count: number
  above_p90_count: number
  used_recommended_count: number
  mean_residual: number
  mean_absolute_residual: number
}

export interface PredictedVsRealizedList {
  items: PredictedVsRealized[]
  total: number
  summary: PredictedVsRealizedSummary
}

export interface SurvivalCurve {
  times: number[]
  survival: number[]
  at_risk: number[]
  events: number[]
  censored: number[]
}

export interface TimeToSellCell {
  channel: string
  grade: string
  sample_size: number
  used_fallback: boolean
  median_days: number | null
  p25_days: number | null
  p75_days: number | null
  expected_days: number | null
  source: string
  as_of: string | null
  curve: SurvivalCurve
}

export interface TimeToSellReport {
  min_sample: number
  items: TimeToSellCell[]
  total: number
  fallback_count: number
  prior_source: string
}

export const CHANNEL_LABELS: Record<string, string> = {
  RESELL_OPEN_BOX: 'Resell as open-box',
  RESELL_REFURB: 'Refurbish and resell',
  PARTS_HARVEST: 'Harvest the parts',
  RECYCLE: 'Recycle',
  DONATE: 'Donate',
  HOLD: 'Hold for a better price',
  SAFE_DEFAULT: 'Safe default - human check needed',
}

export function channelLabel(channel: string): string {
  return CHANNEL_LABELS[channel] ?? channel.replace(/_/g, ' ').toLowerCase()
}

export function channelShortLabel(channel: string): string {
  switch (channel) {
    case 'RESELL_OPEN_BOX':
      return 'Open-box'
    case 'RESELL_REFURB':
      return 'Refurbish'
    case 'PARTS_HARVEST':
      return 'Parts'
    case 'HOLD':
      return 'Hold'
    case 'RECYCLE':
      return 'Recycle'
    case 'DONATE':
      return 'Donate'
    case 'SAFE_DEFAULT':
      return 'Safe default'
    default:
      return channel
  }
}

export function formatMoney(value: number): string {
  const sign = value < 0 ? '-' : ''
  const absolute = Math.abs(value)
  return `${sign}$${absolute.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}
