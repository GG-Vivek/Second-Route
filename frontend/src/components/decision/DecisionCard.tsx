import { useMemo, useState } from 'react'
import { AlertTriangle, Check, ChevronDown, ChevronUp, FlaskConical, Pencil } from 'lucide-react'
import { ConfidenceBar } from '@/components/decision/ConfidenceBar'
import { NetRange } from '@/components/decision/NetRange'
import { OverrideDialog } from '@/components/OverrideDialog'
import { cn } from '@/utils/cn'
import {
  channelLabel,
  channelShortLabel,
  formatMoney,
  formatPercent,
  type Candidate,
  type Decision,
} from '@/types/decision'

interface DecisionCardProps {
  decision: Decision
  /** Called when the operator accepts the recommendation. */
  onAccept?: (decision: Decision) => void
  className?: string
}

function eligibleCandidates(decision: Decision): Candidate[] {
  return decision.candidates.filter((candidate) => candidate.eligible)
}

export function DecisionCard({ decision, onAccept, className }: DecisionCardProps) {
  const [showAllCandidates, setShowAllCandidates] = useState(false)
  const [accepted, setAccepted] = useState(false)
  const [overrideOpen, setOverrideOpen] = useState(false)
  const [overrideMessage, setOverrideMessage] = useState<string | null>(null)

  const eligible = useMemo(() => eligibleCandidates(decision), [decision])
  const recommended = useMemo(
    () => eligible.find((candidate) => candidate.channel === decision.recommended_channel),
    [eligible, decision.recommended_channel]
  )
  const runnerUp = useMemo(() => {
    const others = eligible.filter((candidate) => candidate.channel !== decision.recommended_channel)
    return others.sort((a, b) => b.certainty_equivalent - a.certainty_equivalent)[0]
  }, [eligible, decision.recommended_channel])

  const displayedCandidates = showAllCandidates ? decision.candidates : eligible.slice(0, 3)
  const isSafeDefault = decision.fallback_used || decision.recommended_channel === 'SAFE_DEFAULT'

  return (
    <div className={cn('space-y-6', className)} data-testid="decision-card">
      {/* Prototype banner */}
      <div
        className="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4 text-amber-900"
        role="note"
        data-testid="prototype-badge"
      >
        <FlaskConical className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <div>
          <p className="font-semibold">{decision.prototype_badge}</p>
          <p className="text-sm">
            Prices and costs are synthetic. This card is a prototype of the decision logic, not a
            money claim.
          </p>
        </div>
      </div>

      {/* Headline */}
      <div className="rounded-lg border bg-card p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground">Recommended disposition</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight">
              {channelLabel(decision.recommended_channel)}
            </h2>
            {decision.fallback_used && decision.fallback_channel && (
              <p className="mt-1 text-sm text-muted-foreground">
                Conservative floor: {channelLabel(decision.fallback_channel)}
              </p>
            )}
          </div>
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium',
              isSafeDefault
                ? 'bg-yellow-100 text-yellow-800'
                : 'bg-green-100 text-green-800'
            )}
          >
            {isSafeDefault ? (
              <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <Check className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {isSafeDefault ? 'Needs a human check' : 'Recommendation'}
          </span>
        </div>

        <div className="mt-6">
          <ConfidenceBar
            confidence={decision.confidence}
            fallbackUsed={decision.fallback_used}
          />
        </div>

        {recommended && (
          <div className="mt-6 border-t pt-6">
            <NetRange
              p10={recommended.p10}
              p50={recommended.p50}
              p90={recommended.p90}
              mean={recommended.mean}
              runnerUpMean={runnerUp?.mean}
            />
          </div>
        )}
      </div>

      {/* Alternatives */}
      <section aria-labelledby="alternatives-heading">
        <h3 id="alternatives-heading" className="text-lg font-semibold">
          Alternatives
        </h3>
        <div className="mt-3 overflow-hidden rounded-lg border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left font-medium">
                  Channel
                </th>
                <th scope="col" className="px-4 py-3 text-right font-medium">
                  p50 net
                </th>
                <th scope="col" className="px-4 py-3 text-right font-medium">
                  P(best)
                </th>
                <th scope="col" className="px-4 py-3 text-right font-medium">
                  Delta
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {displayedCandidates.map((candidate) => {
                const delta = recommended ? candidate.mean - recommended.mean : 0
                const isRecommended = candidate.channel === decision.recommended_channel
                return (
                  <tr
                    key={candidate.channel}
                    className={cn(isRecommended && 'bg-primary/5')}
                    data-testid={`candidate-${candidate.channel}`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {channelShortLabel(candidate.channel)}
                        </span>
                        {isRecommended && (
                          <span className="rounded bg-primary px-1.5 py-0.5 text-[10px] font-semibold uppercase text-primary-foreground">
                            Recommended
                          </span>
                        )}
                      </div>
                      {!candidate.eligible && candidate.exclusion_reason && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          {candidate.exclusion_reason}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono">
                      {candidate.eligible ? formatMoney(candidate.p50) : '-'}
                    </td>
                    <td className="px-4 py-3 text-right font-mono">
                      {candidate.eligible ? formatPercent(candidate.probability_best) : '-'}
                    </td>
                    <td
                      className={cn(
                        'px-4 py-3 text-right font-mono',
                        delta > 0 ? 'text-green-600' : delta < 0 ? 'text-muted-foreground' : ''
                      )}
                    >
                      {candidate.eligible ? formatMoney(delta) : '-'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {decision.candidates.length > 3 && (
          <button
            type="button"
            onClick={() => setShowAllCandidates((value) => !value)}
            className="mt-2 inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            {showAllCandidates ? (
              <>
                <ChevronUp className="h-4 w-4" aria-hidden="true" />
                Show fewer channels
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
                Show all {decision.candidates.length} channels
              </>
            )}
          </button>
        )}
      </section>

      {/* Reasons */}
      <section aria-labelledby="reasons-heading">
        <h3 id="reasons-heading" className="text-lg font-semibold">
          Why this channel
        </h3>
        <ul className="mt-3 space-y-2" data-testid="reasons-list">
          {decision.reasons.map((reason) => (
            <li
              key={reason.code}
              className="flex items-start gap-3 rounded-lg border bg-card p-4"
            >
              <span
                className={cn(
                  'mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold',
                  reason.favours_recommended
                    ? 'bg-green-100 text-green-700'
                    : 'bg-muted text-muted-foreground'
                )}
                aria-hidden="true"
              >
                {reason.favours_recommended ? '+' : '-'}
              </span>
              <div>
                <p className="text-sm">{reason.text}</p>
                <p className="mt-0.5 font-mono text-xs text-muted-foreground">
                  {reason.label}: {formatMoney(reason.contribution)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* Flip conditions */}
      {decision.flip_conditions.length > 0 && (
        <section aria-labelledby="flip-heading">
          <h3 id="flip-heading" className="text-lg font-semibold">
            What would change this
          </h3>
          <ul className="mt-3 space-y-2" data-testid="flip-conditions-list">
            {decision.flip_conditions.map((condition) => (
              <li
                key={`${condition.input_name}-${condition.threshold_value}`}
                className="rounded-lg border bg-card p-4"
              >
                <p className="text-sm">{condition.description}</p>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  {condition.input_name}: {String(condition.current_value)} &rarr;{' '}
                  {String(condition.threshold_value)} &rarr; {channelShortLabel(condition.new_channel)}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Action steps */}
      <section aria-labelledby="actions-heading">
        <h3 id="actions-heading" className="text-lg font-semibold">
          Next steps
        </h3>
        <ol className="mt-3 space-y-2" data-testid="action-steps-list">
          {decision.action_steps.map((step) => (
            <li key={step.order} className="flex items-start gap-3 rounded-lg border bg-card p-4">
              <span
                className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground"
                aria-hidden="true"
              >
                {step.order}
              </span>
              <div>
                <p className="text-sm font-medium">{step.title}</p>
                <p className="mt-0.5 text-sm text-muted-foreground">{step.detail}</p>
                {step.reference && (
                  <p className="mt-1 text-xs text-muted-foreground">Reference: {step.reference}</p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Accept */}
      <div className="flex flex-wrap items-center gap-3 border-t pt-6">
        <button
          type="button"
          disabled={accepted}
          onClick={() => {
            setAccepted(true)
            onAccept?.(decision)
          }}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
          data-testid="accept-button"
        >
          <Check className="h-4 w-4" aria-hidden="true" />
          {accepted ? 'Accepted' : 'Accept recommendation'}
        </button>
        <button
          type="button"
          onClick={() => setOverrideOpen(true)}
          className="inline-flex items-center gap-2 rounded-lg border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-accent"
          data-testid="override-button"
        >
          <Pencil className="h-4 w-4" aria-hidden="true" />
          Override
        </button>
        <p className="text-xs text-muted-foreground">
          {overrideMessage
            ? overrideMessage
            : 'Overriding requires a reason. Every decision is logged.'}
        </p>
      </div>

      <OverrideDialog
        decisionId={decision.id}
        recommendedChannel={decision.recommended_channel}
        availableChannels={eligible.map((candidate) => candidate.channel)}
        open={overrideOpen}
        onClose={() => setOverrideOpen(false)}
        onSuccess={(message) => setOverrideMessage(message)}
      />

      {/* Provenance */}
      <details className="rounded-lg border bg-card p-4 text-sm">
        <summary className="cursor-pointer font-medium">
          Data provenance and reproducibility
        </summary>
        <dl className="mt-3 space-y-1 text-muted-foreground">
          <div className="flex justify-between gap-4">
            <dt>Model version</dt>
            <dd className="font-mono">{decision.model_version}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt>Risk profile</dt>
            <dd className="font-mono">{decision.risk_profile}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt>Input snapshot hash</dt>
            <dd className="font-mono break-all">{decision.input_snapshot_hash}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt>Created</dt>
            <dd className="font-mono">{new Date(decision.created_at).toLocaleString()}</dd>
          </div>
        </dl>
        {decision.data_freshness.warnings.length > 0 && (
          <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
            {decision.data_freshness.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        )}
      </details>
    </div>
  )
}
