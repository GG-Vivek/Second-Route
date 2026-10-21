import { api } from '@/api/client'
import type { DecisionDistribution } from '@/types/distribution'
import type {
  CreateDecisionRequest,
  CreateOutcomeRequest,
  CreateOverrideRequest,
  Decision,
  DecisionList,
  Explanation,
  Outcome,
  OutcomeList,
  Override,
  OverrideList,
  PredictedVsRealizedList,
  ReproducibilityResult,
  RegretReport,
  CalibrationReport,
  CalibrationVersion,
  NorthStarReport,
  OverrideRateReport,
  RegretOverTimeReport,
  TimeToSellReport,
} from '@/types/decision'

export type {
  ActionStep,
  Explanation,
  Candidate,
  CostBreakdown,
  CreateDecisionRequest,
  CreateOutcomeRequest,
  CreateOverrideRequest,
  DataFreshness,
  Decision,
  DecisionList,
  DecisionSummary,
  DispositionChannel,
  FlipCondition,
  Grade,
  Outcome,
  OutcomeList,
  Override,
  OverrideList,
  PredictedVsRealized,
  PredictedVsRealizedList,
  PredictedVsRealizedSummary,
  Reason,
  ReproducibilityResult,
  RegretReport,
  CalibrationReport,
  CalibrationVersion,
  NorthStarReport,
  OverrideRateReport,
  RegretOverTimeReport,
  RiskProfile,
  TimeToSellReport,
} from '@/types/decision'

/** Run the decision engine for a unit and store the result. */
export async function createDecision(
  unitId: string,
  data: CreateDecisionRequest = {}
): Promise<Decision> {
  return api.post<Decision>(`/units/${unitId}/decide`, data)
}

/** Read a stored decision. */
export async function getDecision(decisionId: string): Promise<Decision> {
  return api.get<Decision>(`/decisions/${decisionId}`)
}

/** List the decisions recorded for a unit, newest first. */
export async function listUnitDecisions(
  unitId: string,
  params?: { limit?: number; offset?: number }
): Promise<DecisionList> {
  const search = new URLSearchParams()
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  const query = search.toString()
  return api.get<DecisionList>(`/units/${unitId}/decisions${query ? `?${query}` : ''}`)
}

/** Replay a stored decision from its snapshot. */
export async function reproduceDecision(decisionId: string): Promise<ReproducibilityResult> {
  return api.get<ReproducibilityResult>(`/decisions/${decisionId}/reproduce`)
}

/** Record a human override of a decision. The reason is mandatory. */
export async function createOverride(
  decisionId: string,
  data: CreateOverrideRequest
): Promise<Override> {
  return api.post<Override>(`/decisions/${decisionId}/override`, data)
}

/** List the overrides recorded for a decision, newest first. */
export async function listDecisionOverrides(
  decisionId: string,
  params?: { limit?: number; offset?: number }
): Promise<OverrideList> {
  const search = new URLSearchParams()
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  const query = search.toString()
  return api.get<OverrideList>(`/decisions/${decisionId}/overrides${query ? `?${query}` : ''}`)
}

/** List the overrides recorded for a unit, across all its decisions. */
export async function listUnitOverrides(
  unitId: string,
  params?: { limit?: number; offset?: number }
): Promise<OverrideList> {
  const search = new URLSearchParams()
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  const query = search.toString()
  return api.get<OverrideList>(`/units/${unitId}/overrides${query ? `?${query}` : ''}`)
}

/** Record the realized outcome of a dispositioned unit. */
export async function createOutcome(
  unitId: string,
  data: CreateOutcomeRequest
): Promise<Outcome> {
  return api.post<Outcome>(`/units/${unitId}/outcome`, data)
}

/** List the outcomes recorded for a unit, newest first. */
export async function listUnitOutcomes(
  unitId: string,
  params?: { limit?: number; offset?: number }
): Promise<OutcomeList> {
  const search = new URLSearchParams()
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  const query = search.toString()
  return api.get<OutcomeList>(`/units/${unitId}/outcomes${query ? `?${query}` : ''}`)
}

/** List the outcomes linked to a decision, newest first. */
export async function listDecisionOutcomes(
  decisionId: string,
  params?: { limit?: number; offset?: number }
): Promise<OutcomeList> {
  const search = new URLSearchParams()
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  const query = search.toString()
  return api.get<OutcomeList>(`/decisions/${decisionId}/outcomes${query ? `?${query}` : ''}`)
}

/** Compare the predicted net against the realized net for one unit. */
export async function getUnitPredictedVsRealized(
  unitId: string
): Promise<PredictedVsRealizedList> {
  return api.get<PredictedVsRealizedList>(
    `/analytics/units/${unitId}/predicted-vs-realized`
  )
}

/** Compare the predicted net against the realized net across all units. */
export async function getPredictedVsRealized(
  params?: { limit?: number }
): Promise<PredictedVsRealizedList> {
  const search = new URLSearchParams()
  if (params?.limit) search.set('limit', String(params.limit))
  const query = search.toString()
  return api.get<PredictedVsRealizedList>(`/analytics/predicted-vs-realized${query ? `?${query}` : ''}`)
}

/** Fetch the Kaplan-Meier time-to-sell curves by channel and grade. */
export async function getTimeToSell(
  params?: { channel?: string; grade?: string; min_sample?: number }
): Promise<TimeToSellReport> {
  const search = new URLSearchParams()
  if (params?.channel) search.set('channel', params.channel)
  if (params?.grade) search.set('grade', params.grade)
  if (params?.min_sample) search.set('min_sample', String(params.min_sample))
  const query = search.toString()
  return api.get<TimeToSellReport>(`/analytics/time-to-sell${query ? `?${query}` : ''}`)
}

/** Fetch the regret of the recorded dispositions. */
export async function getRegret(params?: { limit?: number }): Promise<RegretReport> {
  const search = new URLSearchParams()
  if (params?.limit) search.set('limit', String(params.limit))
  const query = search.toString()
  return api.get<RegretReport>(`/analytics/regret${query ? `?${query}` : ''}`)
}

/** Fetch the reliability curve and the expected calibration error. */
export async function getCalibration(params?: { bins?: number }): Promise<CalibrationReport> {
  const search = new URLSearchParams()
  if (params?.bins) search.set('bins', String(params.bins))
  const query = search.toString()
  return api.get<CalibrationReport>(`/analytics/calibration${query ? `?${query}` : ''}`)
}

/** Fit a new recalibration version and put it in force. */
export async function recalibrate(params?: {
  bins?: number
  version?: string
}): Promise<CalibrationVersion> {
  const search = new URLSearchParams()
  if (params?.bins) search.set('bins', String(params.bins))
  if (params?.version) search.set('version', params.version)
  const query = search.toString()
  return api.post<CalibrationVersion>(`/analytics/calibration/recalibrate${query ? `?${query}` : ''}`)
}

/** Fetch the north star: the net recovered per return, above the baseline. */
export async function getNorthStar(): Promise<NorthStarReport> {
  return api.get<NorthStarReport>('/analytics/north-star')
}

/** Fetch the regret of every period. */
export async function getRegretOverTime(params?: {
  bucket?: 'month' | 'week'
}): Promise<RegretOverTimeReport> {
  const search = new URLSearchParams()
  if (params?.bucket) search.set('bucket', params.bucket)
  const query = search.toString()
  return api.get<RegretOverTimeReport>(`/analytics/regret-over-time${query ? `?${query}` : ''}`)
}

/** Fetch the override rate and the reasons behind it. */
export async function getOverrideRate(): Promise<OverrideRateReport> {
  return api.get<OverrideRateReport>('/analytics/override-rate')
}

/** The URL of a CSV export. */
export function exportUrl(entity: 'decisions' | 'overrides' | 'outcomes'): string {
  return `/api/v1/export/${entity}`
}

/** Ask for an explanation of a decision, in words. */
export async function explainDecision(decisionId: string): Promise<Explanation> {
  return api.post<Explanation>(`/decisions/${decisionId}/explanation`)
}

/**
 * Fetch the distribution of the net value across every channel.
 *
 * This is the engine's own Monte Carlo output, replayed from the stored
 * snapshot. It is not a fitted curve.
 */
export async function getDecisionDistribution(
  decisionId: string,
  params?: { bins?: number }
): Promise<DecisionDistribution> {
  const search = new URLSearchParams()
  if (params?.bins) search.set('bins', String(params.bins))
  const query = search.toString()
  return api.get<DecisionDistribution>(
    `/decisions/${decisionId}/distribution${query ? `?${query}` : ''}`
  )
}
