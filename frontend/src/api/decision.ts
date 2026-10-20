import { api } from '@/api/client'
import type {
  CreateDecisionRequest,
  CreateOverrideRequest,
  Decision,
  DecisionList,
  Override,
  OverrideList,
  ReproducibilityResult,
} from '@/types/decision'

export type {
  ActionStep,
  Candidate,
  CostBreakdown,
  CreateDecisionRequest,
  CreateOverrideRequest,
  DataFreshness,
  Decision,
  DecisionList,
  DecisionSummary,
  DispositionChannel,
  FlipCondition,
  Grade,
  Override,
  OverrideList,
  Reason,
  ReproducibilityResult,
  RiskProfile,
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
