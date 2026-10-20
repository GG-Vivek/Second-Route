import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Loader2, Play, ClipboardCheck } from 'lucide-react'
import { DecisionCard } from '@/components/decision/DecisionCard'
import { OutcomeDialog } from '@/components/OutcomeDialog'
import { PredictedVsRealizedPanel } from '@/components/decision/PredictedVsRealizedPanel'
import {
  createDecision,
  getDecision,
  listUnitDecisions,
  getUnitPredictedVsRealized,
} from '@/api/decision'
import { Button } from '@/components/ui/button'
import type { RiskProfile } from '@/types/decision'

const RISK_PROFILES: RiskProfile[] = ['conservative', 'balanced', 'aggressive']

export function DecisionPage() {
  const { id: unitId } = useParams<{ id: string }>()
  const [riskProfile, setRiskProfile] = useState<RiskProfile>('balanced')
  const [activeDecisionId, setActiveDecisionId] = useState<string | null>(null)
  const [outcomeOpen, setOutcomeOpen] = useState(false)
  const [outcomeMessage, setOutcomeMessage] = useState<string | null>(null)

  const decisionsQuery = useQuery({
    queryKey: ['unit-decisions', unitId],
    queryFn: () => listUnitDecisions(unitId ?? ''),
    enabled: Boolean(unitId),
  })

  const decisionQuery = useQuery({
    queryKey: ['decision', activeDecisionId],
    queryFn: () => getDecision(activeDecisionId as string),
    enabled: Boolean(activeDecisionId),
  })

  const predictedVsRealizedQuery = useQuery({
    queryKey: ['predicted-vs-realized', unitId],
    queryFn: () => getUnitPredictedVsRealized(unitId ?? ''),
    enabled: Boolean(unitId),
  })

  const latestId = decisionsQuery.data?.items?.[0]?.id ?? null
  const shownId = activeDecisionId ?? latestId

  const showSpinner = decisionsQuery.isLoading || (shownId && decisionQuery.isLoading)

  if (!unitId) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
        No unit was selected.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Disposition decision</h1>
          <p className="text-muted-foreground mt-1">
            One return in, one disposition instruction out.
          </p>
        </div>

        <div className="flex items-end gap-3">
          <div>
            <label
              htmlFor="risk-profile"
              className="mb-1 block text-xs font-medium text-muted-foreground"
            >
              Risk profile
            </label>
            <select
              id="risk-profile"
              value={riskProfile}
              onChange={(event) => setRiskProfile(event.target.value as RiskProfile)}
              className="h-9 rounded-lg border border-input bg-background px-3 text-sm"
            >
              {RISK_PROFILES.map((profile) => (
                <option key={profile} value={profile}>
                  {profile}
                </option>
              ))}
            </select>
          </div>

          <Button
            type="button"
            onClick={() => {
              createDecision(unitId, { risk_profile: riskProfile })
                .then((decision) => {
                  setActiveDecisionId(decision.id)
                  void decisionsQuery.refetch()
                })
                .catch(() => undefined)
            }}
            data-testid="run-decision"
          >
            <Play className="h-4 w-4" aria-hidden="true" />
            Run decision
          </Button>
        </div>
      </div>

      {showSpinner && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading the decision...
        </div>
      )}

      {decisionQuery.isError && (
        <div
          className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800"
          role="alert"
        >
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">The decision could not be loaded</p>
            <p className="text-sm">Run the decision for this unit first.</p>
          </div>
        </div>
      )}

      {!showSpinner && decisionQuery.data && (
        <>
          <DecisionCard decision={decisionQuery.data} />
          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setOutcomeOpen(true)}
              data-testid="record-outcome"
            >
              <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
              Record outcome
            </Button>
            {outcomeMessage && (
              <p className="text-sm text-muted-foreground">{outcomeMessage}</p>
            )}
          </div>
          <OutcomeDialog
            unitId={unitId}
            decisionId={decisionQuery.data.id}
            recommendedChannel={decisionQuery.data.recommended_channel}
            availableChannels={decisionQuery.data.candidates
              .filter((candidate) => candidate.eligible)
              .map((candidate) => candidate.channel)}
            open={outcomeOpen}
            onClose={() => setOutcomeOpen(false)}
            onSuccess={setOutcomeMessage}
          />
        </>
      )}

      {!showSpinner && !decisionQuery.data && decisionsQuery.data?.total === 0 && (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <p className="font-medium">No decision yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Run the decision engine to get a disposition recommendation for this unit.
          </p>
        </div>
      )}

      {decisionsQuery.data && decisionsQuery.data.total > 0 && (
        <section aria-labelledby="history-heading">
          <h2 id="history-heading" className="text-lg font-semibold">
            Decision history
          </h2>
          <ul className="mt-3 space-y-2">
            {decisionsQuery.data.items.map((summary) => (
              <li key={summary.id}>
                <button
                  type="button"
                  onClick={() => setActiveDecisionId(summary.id)}
                  className="flex w-full items-center justify-between gap-4 rounded-lg border bg-card p-3 text-left text-sm hover:bg-accent"
                >
                  <span className="font-medium">{summary.recommended_channel}</span>
                  <span className="font-mono text-muted-foreground">
                    {(summary.confidence * 100).toFixed(1)}% - {summary.risk_profile}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {predictedVsRealizedQuery.data && (
        <PredictedVsRealizedPanel
          comparisons={predictedVsRealizedQuery.data.items}
          summary={predictedVsRealizedQuery.data.summary}
        />
      )}
    </div>
  )
}
