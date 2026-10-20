import { useState } from 'react'
import { MessageSquareText, Sparkles, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/utils/cn'
import { explainDecision } from '@/api/decision'
import type { Explanation } from '@/types/decision'

interface ExplanationPanelProps {
  decisionId: string
  /** The explanation, when one has already been fetched. */
  explanation?: Explanation | null
  /** Called when the explanation is fetched. */
  onExplained?: (explanation: Explanation) => void
}

const SOURCE_LABELS: Record<string, string> = {
  model: 'Written by the model',
  template: 'The standard template',
}

const REASON_LABELS: Record<string, string> = {
  validated: 'Every number in it came from the decision',
  'unseen-number': 'The model mentioned a number the decision does not have',
  'no-model': 'No model was available',
  'model-error': 'The model could not be reached',
  'model-timeout': 'The model took too long',
  'empty-output': 'The model said nothing',
  disabled: 'Explanations from the model are switched off',
}

/**
 * The explanation of a decision, in words.
 *
 * The explanation is written by the model or by the standard template,
 * and the panel says which: a reader has to be able to tell a paragraph
 * the engine wrote from one a model wrote.
 */
export function ExplanationPanel({
  decisionId,
  explanation: existing,
  onExplained,
}: ExplanationPanelProps) {
  const [explanation, setExplanation] = useState<Explanation | null>(existing ?? null)
  const [pending, setPending] = useState(false)
  const [failed, setFailed] = useState(false)

  async function ask() {
    setPending(true)
    setFailed(false)
    try {
      const result = await explainDecision(decisionId)
      setExplanation(result)
      onExplained?.(result)
    } catch {
      setFailed(true)
    } finally {
      setPending(false)
    }
  }

  if (!explanation) {
    return (
      <section aria-labelledby="explanation-heading" data-testid="explanation-panel">
        <h3 id="explanation-heading" className="text-lg font-semibold">
          Why this channel
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          A short explanation of the decision, in words.
        </p>
        <Button
          type="button"
          variant="secondary"
          className="mt-3"
          onClick={ask}
          disabled={pending}
          data-testid="explain-button"
        >
          <MessageSquareText className="h-4 w-4" aria-hidden="true" />
          {pending ? 'Thinking...' : 'Explain this decision'}
        </Button>
        {failed && (
          <p className="mt-2 text-sm text-destructive" data-testid="explanation-error">
            The explanation could not be produced.
          </p>
        )}
      </section>
    )
  }

  const fromModel = explanation.source === 'model'

  return (
    <section aria-labelledby="explanation-heading" data-testid="explanation-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="explanation-heading" className="text-lg font-semibold">
          Why this channel
        </h3>
        <span
          className={cn(
            'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium',
            fromModel ? 'bg-violet-100 text-violet-800' : 'bg-slate-100 text-slate-700'
          )}
          data-testid="explanation-source"
        >
          {fromModel ? (
            <Sparkles className="h-3 w-3" aria-hidden="true" />
          ) : (
            <MessageSquareText className="h-3 w-3" aria-hidden="true" />
          )}
          {SOURCE_LABELS[explanation.source] ?? explanation.source}
        </span>
      </div>

      <p className="mt-3 whitespace-pre-line text-sm" data-testid="explanation-text">
        {explanation.text}
      </p>

      <p className="mt-2 text-xs text-muted-foreground" data-testid="explanation-reason">
        {REASON_LABELS[explanation.reason] ?? explanation.reason}
      </p>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="mt-2"
        onClick={ask}
        disabled={pending}
        data-testid="explain-again"
      >
        <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
        {pending ? 'Thinking...' : 'Explain again'}
      </Button>
    </section>
  )
}
