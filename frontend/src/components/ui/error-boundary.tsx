import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'

export interface ErrorBoundaryProps {
  children: ReactNode
  /** Shown instead of the children when something goes wrong. */
  fallback?: (error: Error, reset: () => void) => ReactNode
  /** Called when something goes wrong, so that it can be reported. */
  onError?: (error: Error, info: ErrorInfo) => void
}

interface ErrorBoundaryState {
  error: Error | null
}

/**
 * The error boundary.
 *
 * Without one, a single bad field in a response takes the whole
 * application down and leaves a blank page. With one, the page that
 * contains the bad field fails and the rest of the application carries
 * on.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.props.onError?.(error, info)
    console.error('Something went wrong while rendering:', error)
  }

  reset = () => {
    this.setState({ error: null })
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    if (this.props.fallback) return this.props.fallback(error, this.reset)

    return (
      <div
        className="flex flex-col items-start gap-3 rounded-4xl border border-destructive/40 bg-destructive/5 p-6"
        role="alert"
      >
        <p className="flex items-center gap-2 font-medium">
          <AlertTriangle className="size-4 text-destructive" aria-hidden="true" />
          This part of the page could not be shown.
        </p>
        <p className="text-sm text-muted-foreground">
          {error.message || 'Something went wrong while the page was being drawn.'}
        </p>
        <button
          type="button"
          onClick={this.reset}
          className="rounded-4xl bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/80"
        >
          Try again
        </button>
      </div>
    )
  }
}
