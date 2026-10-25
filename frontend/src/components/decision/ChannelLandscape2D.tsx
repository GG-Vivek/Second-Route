import { useMemo, useState, type PointerEvent } from 'react'
import { cn } from '@/utils/cn'
import { seriesHue } from '@/theme/meaning'
import { channelShortLabel, formatMoney } from '@/types/decision'
import { decisionChannels, focusAxis } from '@/types/distribution'
import type { ChannelDistribution, DecisionDistribution } from '@/types/distribution'

export interface ChannelLandscape2DProps {
  distribution: DecisionDistribution
  /** The channel the engine recommended. */
  recommendedChannel: string
  className?: string
}

/** The drawing surface, in the units of the view box. */
const WIDTH = 960
const HEIGHT = 300
const PAD_LEFT = 18
const PAD_RIGHT = 18
const PAD_TOP = 30
const PAD_BOTTOM = 38

/** How close two labels may be before one of them is moved. */
const LABEL_MIN_DX = 46
const LABEL_MIN_DY = 13

interface PlacedLabel {
  channel: string
  x: number
  y: number
  index: number
  isRecommended: boolean
}

/**
 * The channel landscape, drawn flat.
 *
 * Every channel's density is drawn against the same axis, so the overlap
 * between two channels is a shape rather than a number. The overlap is
 * what the confidence is made of: the wider the overlap, the less the
 * recommendation can be trusted.
 *
 * Each curve is scaled to its own peak rather than to the tallest curve
 * of them all. A channel with a narrow spread has a high peak and a wide
 * channel has a low one, so a shared scale would flatten the two channels
 * that matter into nothing. The real densities are in the readout and in
 * the table of alternatives.
 *
 * This is the accessible view and the fallback. It is not a simplified
 * version of the three-dimensional one: it is the same data, and it is
 * the one that is always available.
 */
export function ChannelLandscape2D({
  distribution,
  recommendedChannel,
  className,
}: ChannelLandscape2DProps) {
  const [hoverX, setHoverX] = useState<number | null>(null)

  // The range the decision is made in, and the channels that fall in it.
  const axis = useMemo(() => focusAxis(distribution), [distribution])

  const eligible = useMemo(
    () =>
      decisionChannels(distribution).filter((channel) =>
        channel.bins.some((bin) => bin.x >= axis.min && bin.x <= axis.max)
      ),
    [distribution, axis.min, axis.max]
  )

  const span = axis.max - axis.min || 1
  const plotWidth = WIDTH - PAD_LEFT - PAD_RIGHT
  const plotHeight = HEIGHT - PAD_TOP - PAD_BOTTOM

  const toX = (value: number) => PAD_LEFT + ((value - axis.min) / span) * plotWidth

  /**
   * The colour a channel is drawn in, written the way the stylesheet
   * writes its tokens, so that a curve, its name, its marker and its dot
   * in the readout are all the same colour in either theme (F11.8).
   */
  const colourFor = (index: number, isRecommended: boolean) =>
    `rgb(var(--${seriesHue(index, isRecommended)}))`

  /** The peak of each channel, which is what its own curve is scaled to. */
  const peakOf = useMemo(() => {
    const peaks = new Map<string, number>()
    for (const channel of eligible) {
      let highest = 0
      for (const bin of channel.bins) {
        if (bin.density > highest) highest = bin.density
      }
      peaks.set(channel.channel, highest || 1)
    }
    return peaks
  }, [eligible])

  const toY = (density: number, channelPeak: number) =>
    PAD_TOP + plotHeight - (density / (channelPeak || 1)) * plotHeight

  const pathFor = (channel: ChannelDistribution): string => {
    if (channel.bins.length === 0) return ''
    const peak = peakOf.get(channel.channel) ?? 1
    const points = channel.bins.map(
      (bin) => `${toX(bin.x).toFixed(2)},${toY(bin.density, peak).toFixed(2)}`
    )
    const first = channel.bins[0]
    const last = channel.bins[channel.bins.length - 1]
    return [
      `M ${toX(first.x).toFixed(2)},${(PAD_TOP + plotHeight).toFixed(2)}`,
      `L ${points.join(' L ')}`,
      `L ${toX(last.x).toFixed(2)},${(PAD_TOP + plotHeight).toFixed(2)}`,
      'Z',
    ].join(' ')
  }

  /**
   * The labels.
   *
   * Two channels can peak at the same point, so a label that would sit on
   * top of one that is already placed is moved up until it does not.
   */
  const labels = useMemo(() => {
    const placed: PlacedLabel[] = []
    const axisMin = axis.min
    const axisMax = axis.max
    const axisSpan = axisMax - axisMin || 1
    const plotWidthLocal = WIDTH - PAD_LEFT - PAD_RIGHT
    const plotHeightLocal = HEIGHT - PAD_TOP - PAD_BOTTOM

    const candidates = eligible.map((channel, index) => {
      const peak = peakOf.get(channel.channel) ?? 1
      const top = channel.bins.reduce((best, bin) =>
        bin.density > best.density ? bin : best
      )
      return {
        channel: channel.channel,
        index,
        x: PAD_LEFT + ((top.x - axisMin) / axisSpan) * plotWidthLocal,
        y:
          PAD_TOP +
          plotHeightLocal -
          (top.density / (peak || 1)) * plotHeightLocal -
          6,
        isRecommended: channel.channel === recommendedChannel,
      }
    })

    for (const candidate of candidates) {
      let attempts = 0
      while (
        attempts < 8 &&
        placed.some(
          (other) =>
            Math.abs(other.x - candidate.x) < LABEL_MIN_DX &&
            Math.abs(other.y - candidate.y) < LABEL_MIN_DY
        )
      ) {
        candidate.y -= LABEL_MIN_DY
        attempts += 1
      }
      placed.push(candidate)
    }
    return placed
  }, [eligible, peakOf, recommendedChannel, axis.min, axis.max])

  const recommended = eligible.find((c) => c.channel === recommendedChannel)

  const onPointerMove = (event: PointerEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    if (rect.width === 0) return
    const fraction = (event.clientX - rect.left) / rect.width
    const svgX = fraction * WIDTH
    if (svgX < PAD_LEFT || svgX > WIDTH - PAD_RIGHT) {
      setHoverX(null)
      return
    }
    setHoverX(axis.min + ((svgX - PAD_LEFT) / plotWidth) * span)
  }

  const binAt = (channel: ChannelDistribution, x: number) =>
    channel.bins.reduce((best, bin) =>
      Math.abs(bin.x - x) < Math.abs(best.x - x) ? bin : best
    )

  return (
    <div className={cn('space-y-3', className)}>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full touch-none select-none"
        role="img"
        aria-label={
          `The distribution of the net value for ${eligible.length} channels. ` +
          `The recommended channel is ${channelShortLabel(recommendedChannel)}. ` +
          `Each curve is scaled to its own peak so that the shapes can be compared. ` +
          `The numbers are in the table below.`
        }
        onPointerMove={onPointerMove}
        onPointerLeave={() => setHoverX(null)}
        data-testid="channel-landscape-2d"
      >
        {/* The grid. */}
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
          const y = PAD_TOP + plotHeight * fraction
          return (
            <line
              key={fraction}
              x1={PAD_LEFT}
              x2={WIDTH - PAD_RIGHT}
              y1={y}
              y2={y}
              stroke="rgb(var(--border))"
              strokeWidth="1"
              strokeDasharray={fraction === 1 ? undefined : '3 5'}
            />
          )
        })}

        {/* The densities. */}
        {eligible.map((channel, index) => {
          const isRecommended = channel.channel === recommendedChannel
          const colour = colourFor(index, isRecommended)
          return (
            <path
              key={channel.channel}
              d={pathFor(channel)}
              fill={colour}
              fillOpacity={isRecommended ? 0.42 : 0.16}
              stroke={colour}
              strokeOpacity={isRecommended ? 1 : 0.5}
              strokeWidth={isRecommended ? 1.6 : 1}
              data-testid={`landscape-curve-${channel.channel}`}
            />
          )
        })}

        {/* The name of each channel, at the top of its own curve. */}
        {labels.map((label) => (
          <text
            key={label.channel}
            x={label.x}
            y={Math.max(label.y, 12)}
            textAnchor="middle"
            fontSize="12"
            fontWeight={label.isRecommended ? 600 : 400}
            fill={colourFor(label.index, label.isRecommended)}
            fillOpacity={label.isRecommended ? 1 : 0.85}
          >
            {channelShortLabel(label.channel)}
          </text>
        ))}

        {/* The crosshair. */}
        {hoverX !== null && (
          <g>
            <line
              x1={toX(hoverX)}
              x2={toX(hoverX)}
              y1={PAD_TOP}
              y2={PAD_TOP + plotHeight}
              stroke="rgb(var(--foreground))"
              strokeOpacity="0.35"
              strokeWidth="1"
            />
            {eligible.map((channel, index) => {
              const bin = binAt(channel, hoverX)
              const peak = peakOf.get(channel.channel) ?? 1
              return (
                <circle
                  key={`marker-${channel.channel}`}
                  cx={toX(bin.x)}
                  cy={toY(bin.density, peak)}
                  r="3"
                  fill={colourFor(index, channel.channel === recommendedChannel)}
                />
              )
            })}
          </g>
        )}

        {/* The axis. */}
        <line
          x1={PAD_LEFT}
          x2={WIDTH - PAD_RIGHT}
          y1={PAD_TOP + plotHeight}
          y2={PAD_TOP + plotHeight}
          stroke="rgb(var(--border))"
          strokeWidth="1"
        />

        {/* The marks of the recommended channel. */}
        {recommended &&
          ([recommended.p10, recommended.p50, recommended.p90] as const).map((value, index) => (
            <g key={index}>
              <line
                x1={toX(value)}
                x2={toX(value)}
                y1={PAD_TOP + plotHeight}
                y2={PAD_TOP + plotHeight + 6}
                stroke="rgb(var(--primary))"
                strokeWidth="1.5"
              />
              <text
                x={toX(value)}
                y={PAD_TOP + plotHeight + 20}
                textAnchor="middle"
                fontSize="11"
                fontFamily="var(--font-mono)"
                fill="rgb(var(--muted-foreground))"
              >
                {formatMoney(value)}
              </text>
            </g>
          ))}

        <text
          x={PAD_LEFT}
          y={HEIGHT - 4}
          fontSize="11"
          fill="rgb(var(--muted-foreground))"
        >
          {formatMoney(axis.min)}
        </text>
        <text
          x={WIDTH - PAD_RIGHT}
          y={HEIGHT - 4}
          textAnchor="end"
          fontSize="11"
          fill="rgb(var(--muted-foreground))"
        >
          {formatMoney(axis.max)}
        </text>
      </svg>

      {/* The readout, which is also the text alternative for the pointer. */}
      <div className="min-h-[2.5rem] text-xs text-muted-foreground">
        {hoverX === null ? (
          <p>
            Each curve is scaled to its own peak, so the shapes compare rather than the heights.
            The wider two curves overlap, the less the recommendation can be trusted.
          </p>
        ) : (
          <ul className="flex flex-wrap gap-x-6 gap-y-1">
            <li className="font-mono text-foreground">{formatMoney(hoverX)}</li>
            {eligible.map((channel, index) => {
              const bin = binAt(channel, hoverX)
              return (
                <li key={channel.channel} className="flex items-center gap-1.5">
                  <span
                    className="size-2 rounded-full"
                    style={{
                      background: colourFor(index, channel.channel === recommendedChannel),
                    }}
                    aria-hidden="true"
                  />
                  <span>{channelShortLabel(channel.channel)}</span>
                  <span className="font-mono">{bin.density.toFixed(4)}</span>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
