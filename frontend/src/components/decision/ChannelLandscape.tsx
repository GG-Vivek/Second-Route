import { Component, Suspense, lazy, useMemo, useState, type ReactNode } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/utils/cn'
import { supportsWebGL } from '@/three/webgl'
import type { DecisionDistribution } from '@/types/distribution'
import { ChannelLandscape2D } from './ChannelLandscape2D'

// The three-dimensional scene is only fetched when it is asked for. The
// three.js bundle is a quarter of a megabyte and the rest of the
// application does not need it.
const ChannelLandscapeCanvas = lazy(() => import('@/three/ChannelLandscapeCanvas'))

export interface ChannelLandscapeProps {
  distribution: DecisionDistribution
  /** The channel the engine recommended. */
  recommendedChannel: string
  className?: string
}

/**
 * The canvas boundary.
 *
 * react-three-fiber swallows a failure to create a WebGL context, so a
 * failure inside the scene would leave a blank rectangle with no
 * explanation. This boundary catches it and hands the reader the flat
 * view, which carries the same data.
 */
class CanvasBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { failed: boolean }
> {
  constructor(props: { children: ReactNode; fallback: ReactNode }) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: unknown) {
    // The failure is real and it belongs in the log, not in a blank
    // rectangle.
    console.error('The three-dimensional landscape could not be drawn:', error)
  }

  render() {
    if (this.state.failed) return this.props.fallback
    return this.props.children
  }
}

/**
 * The channel landscape.
 *
 * The question the operator actually has is "how much do these channels
 * overlap", and the overlap is what the confidence is made of. The
 * landscape draws it as a shape.
 *
 * It is drawn in three dimensions where the browser can, and flat where it
 * cannot. The flat view is not a lesser version: it is the same data, and
 * it is always available.
 */
export function ChannelLandscape({
  distribution,
  recommendedChannel,
  className,
}: ChannelLandscapeProps) {
  const webgl = useMemo(() => supportsWebGL(), [])
  const [spatial, setSpatial] = useState(webgl)

  const flat = (
    <ChannelLandscape2D
      distribution={distribution}
      recommendedChannel={recommendedChannel}
    />
  )

  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-medium">The channel landscape</h3>
          <p className="text-sm text-muted-foreground">
            The wider two curves overlap, the less the recommendation can be trusted.
          </p>
        </div>

        <div
          className="inline-flex items-center rounded-full bg-muted p-1"
          role="group"
          aria-label="How to draw the landscape"
        >
          <button
            type="button"
            onClick={() => setSpatial(false)}
            aria-pressed={!spatial}
            className={cn(
              'rounded-full px-3 py-1 text-sm font-medium transition-colors',
              !spatial
                ? 'bg-background text-foreground shadow-xs dark:bg-input/30'
                : 'text-muted-foreground hover:text-foreground'
            )}
            data-testid="landscape-flat"
          >
            Flat
          </button>
          <button
            type="button"
            onClick={() => setSpatial(true)}
            aria-pressed={spatial}
            disabled={!webgl}
            title={webgl ? undefined : 'This browser cannot draw in three dimensions'}
            className={cn(
              'rounded-full px-3 py-1 text-sm font-medium transition-colors',
              spatial
                ? 'bg-background text-foreground shadow-xs dark:bg-input/30'
                : 'text-muted-foreground hover:text-foreground',
              !webgl && 'cursor-not-allowed opacity-40 hover:text-muted-foreground'
            )}
            data-testid="landscape-spatial"
          >
            Spatial
          </button>
        </div>
      </div>

      {spatial && webgl ? (
        <CanvasBoundary fallback={flat}>
          <div
            className="mx-auto h-[32rem] w-full max-w-4xl overflow-hidden rounded-4xl border bg-card"
            data-testid="channel-landscape-3d"
          >
            {/*
              The text alternative for the canvas. A reader who cannot see
              the picture is told what the picture shows and where the
              numbers are.
            */}
            <p className="sr-only">
              The net value distribution of the recommended channel and the channels that
              overlap it, drawn in three dimensions. The same information is in the flat view
              and the table of alternatives below.
            </p>
            <Suspense
              fallback={
                <div className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Loading the landscape...
                </div>
              }
            >
              <ChannelLandscapeCanvas
                distribution={distribution}
                recommendedChannel={recommendedChannel}
              />
            </Suspense>
          </div>
        </CanvasBoundary>
      ) : (
        flat
      )}

      {!webgl && (
        <p className="text-xs text-muted-foreground">
          This browser cannot draw in three dimensions, so the landscape is drawn flat. The
          numbers are the same either way.
        </p>
      )}
    </div>
  )
}
