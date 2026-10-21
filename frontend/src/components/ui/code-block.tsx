import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { cn } from '@/utils/cn'

export interface CodeBlockProps {
  /** The code. */
  code: string
  /** The name shown in the header. */
  filename?: string
  /** The language, for the reader. */
  language?: string
  /** Whether the copy button is offered. */
  copyable?: boolean
  className?: string
}

/**
 * The code island.
 *
 * Always dark, in both themes. The point of it is to read as a different
 * kind of thing from the prose around it, so it keeps its own background
 * rather than following the surface.
 */
export function CodeBlock({
  code,
  filename,
  language,
  copyable = false,
  className,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      // A browser that will not give the clipboard is not a failure worth
      // interrupting the reader for.
      setCopied(false)
    }
  }

  return (
    <figure
      className={cn(
        'group/code relative my-0 overflow-hidden rounded-2xl bg-code text-code-foreground',
        className
      )}
    >
      {(filename || copyable) && (
        <div className="flex items-center justify-between gap-3 border-b border-code-foreground/10 px-4 py-2">
          <span className="font-mono text-xs text-code-foreground/60">
            {filename ?? language ?? ''}
          </span>
          {copyable && (
            <button
              type="button"
              onClick={() => void copy()}
              className="flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs text-code-foreground/60 transition-colors hover:bg-code-foreground/10 hover:text-code-foreground"
              aria-label={copied ? 'Copied' : 'Copy to the clipboard'}
            >
              {copied ? (
                <Check className="size-3" aria-hidden="true" />
              ) : (
                <Copy className="size-3" aria-hidden="true" />
              )}
              {copied ? 'Copied' : 'Copy'}
            </button>
          )}
        </div>
      )}
      <pre className="overflow-x-auto p-6 font-mono text-sm leading-relaxed scroll-fade-x">
        <code>{code}</code>
      </pre>
    </figure>
  )
}
