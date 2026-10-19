import { api } from '@/api/client'
import type {
  CreateDecisionRequest,
  Decision,
  DecisionList,
  ReproducibilityResult,
} from '@/types/decision'

export type {
  ActionStep,
  Candidate,
  CostBreakdown,
  CreateDecisionRequest,
  DataFreshness,
  Decision,
  DecisionList,
  DecisionSummary,
  DispositionChannel,
  FlipCondition,
  Grade,
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
