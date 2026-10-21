import { useMemo, useState } from 'react'
import { AlertTriangle, Check, ChevronDown, ChevronUp, Pencil } from 'lucide-react'
import { cn } from '@/utils/cn'
import { ChannelLandscape } from '@/components/decision/ChannelLandscape'
import { ConfidenceBar } from '@/components/decision/ConfidenceBar'
import { ExplanationPanel } from '@/components/decision/ExplanationPanel'
import { NetRange } from '@/components/decision/NetRange'
import { OverrideDialog } from '@/components/OverrideDialog'
import {
  Badge,
  Button,
  Callout,
  Card,
  CardContent,
  CardHeader,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui'
import {
  channelLabel,
  channelShortLabel,
  formatMoney,
  formatPercent,
  type Candidate,
  type Decision,
} from '@/types/decision'
import type { DecisionDistribution } from '@/types/distribution'

interface DecisionCardProps {
  decision: Decision
  /**
   * The distribution of the net value, when it has been fetched. The
   * landscape is drawn from it, so without it the card simply has no
   * landscape.
   */
  distribution?: DecisionDistribution | null
  /** Called when the operator accepts the recommendation. */
  onAccept?: (decision: Decision) => void
  className?: string
}

function eligibleCandidates(decision: Decision): Candidate[] {
  return decision.candidates.filter((candidate) => candidate.eligible)
}

export function DecisionCard({
  decision,
  distribution,
  onAccept,
  className,
}: DecisionCardProps) {
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
      {/* The prototype banner. */}
      <Callout tone="warning" testId="prototype-badge" title={decision.prototype_badge}>
        <p>
          Prices and costs are synthetic. This card is a prototype of the decision logic, not a
          money claim.
        </p>
      </Callout>

      {/* The headline. */}
      <Card>
        <CardHeader className="gap-4">
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
            <Badge variant={isSafeDefault ? 'yellow' : 'lime'}>
              {isSafeDefault ? (
                <AlertTriangle className="size-3" aria-hidden="true" />
              ) : (
                <Check className="size-3" aria-hidden="true" />
              )}
              {isSafeDefault ? 'Needs a human check' : 'Recommendation'}
            </Badge>
          </div>

          <ConfidenceBar
            confidence={decision.confidence}
            fallbackUsed={decision.fallback_used}
          />

          {recommended && (
            <NetRange
              p10={recommended.p10}
              p50={recommended.p50}
              p90={recommended.p90}
              mean={recommended.mean}
              runnerUpMean={runnerUp?.mean}
            />
          )}
        </CardHeader>
      </Card>

      {/* The landscape. */}
      {distribution && (
        <Card>
          <CardContent>
            <ChannelLandscape
              distribution={distribution}
              recommendedChannel={decision.recommended_channel}
            />
          </CardContent>
        </Card>
      )}

      {/* The alternatives. */}
      <section aria-labelledby="alternatives-heading">
        <h3 id="alternatives-heading" className="text-lg font-semibold">
          Alternatives
        </h3>
        <div className="mt-3 overflow-hidden rounded-4xl border bg-card shadow-md ring-1 ring-foreground/5 dark:ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Channel</TableHead>
                <TableHead className="text-right">p50 net</TableHead>
                <TableHead className="text-right">P(best)</TableHead>
                <TableHead className="text-right">Delta</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayedCandidates.map((candidate) => {
                const delta = recommended ? candidate.mean - recommended.mean : 0
                const isRecommended = candidate.channel === decision.recommended_channel
                return (
                  <TableRow
                    key={candidate.channel}
                    className={cn(isRecommended && 'bg-primary/5')}
                    data-testid={`candidate-${candidate.channel}`}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {channelShortLabel(candidate.channel)}
                        </span>
                        {isRecommended && <Badge variant="lime">Recommended</Badge>}
                      </div>
                      {!candidate.eligible && candidate.exclusion_reason && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          {candidate.exclusion_reason}
                        </p>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {candidate.eligible ? formatMoney(candidate.p50) : '-'}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {candidate.eligible ? formatPercent(candidate.probability_best) : '-'}
                    </TableCell>
                    <TableCell
                      className={cn(
                        'text-right font-mono',
                        delta > 0 ? 'text-emerald-600' : delta < 0 ? 'text-muted-foreground' : ''
                      )}
                    >
                      {candidate.eligible ? formatMoney(delta) : '-'}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
        {decision.candidates.length > 3 && (
          <button
            type="button"
            onClick={() => setShowAllCandidates((value) => !value)}
            className="mt-2 inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            {showAllCandidates ? (
              <>
                <ChevronUp className="size-4" aria-hidden="true" />
                Show fewer channels
              </>
            ) : (
              <>
                <ChevronDown className="size-4" aria-hidden="true" />
                Show all {decision.candidates.length} channels
              </>
            )}
          </button>
        )}
      </section>

      {/* The reasons. */}
      <section aria-labelledby="reasons-heading">
        <h3 id="reasons-heading" className="text-lg font-semibold">
          Why this channel
        </h3>
        <ul className="mt-3 space-y-2" data-testid="reasons-list">
          {decision.reasons.map((reason) => (
            <li
              key={reason.code}
              className="flex items-start gap-3 rounded-2xl border bg-card p-4"
            >
              <span
                className={cn(
                  'mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold',
                  reason.favours_recommended
                    ? 'bg-lime-container text-on-primary-container'
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

      {/* The flip conditions. */}
      {decision.flip_conditions.length > 0 && (
        <section aria-labelledby="flip-heading">
          <h3 id="flip-heading" className="text-lg font-semibold">
            What would change this
          </h3>
          <ul className="mt-3 space-y-2" data-testid="flip-conditions-list">
            {decision.flip_conditions.map((condition) => (
              <li
                key={`${condition.input_name}-${condition.threshold_value}`}
                className="rounded-2xl border bg-card p-4"
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

      {/* The action steps. */}
      <section aria-labelledby="actions-heading">
        <h3 id="actions-heading" className="text-lg font-semibold">
          Next steps
        </h3>
        <ol className="mt-3 space-y-2" data-testid="action-steps-list">
          {decision.action_steps.map((step) => (
            <li
              key={step.order}
              className="flex items-start gap-3 rounded-2xl border bg-card p-4"
            >
              <span
                className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary font-mono text-xs font-semibold text-primary-foreground"
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

      {/* The explanation. */}
      <ExplanationPanel decisionId={decision.id} />

      {/* The actions. */}
      <div className="flex flex-wrap items-center gap-3 border-t pt-6">
        <Button
          onClick={() => {
            setAccepted(true)
            onAccept?.(decision)
          }}
          disabled={accepted}
          data-testid="accept-button"
        >
          <Check className="size-4" aria-hidden="true" />
          {accepted ? 'Accepted' : 'Accept recommendation'}
        </Button>
        <Button variant="outline" onClick={() => setOverrideOpen(true)} data-testid="override-button">
          <Pencil className="size-4" aria-hidden="true" />
          Override
        </Button>
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

      {/* The provenance. */}
      <details className="rounded-2xl border bg-card p-4 text-sm">
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
