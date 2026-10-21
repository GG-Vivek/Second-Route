import { Html } from '@react-three/drei'
import { channelShortLabel } from '@/types/decision'
import type { ChannelDistribution } from '@/types/distribution'

export interface ChannelLabelsProps {
  channels: ChannelDistribution[]
  axisMin: number
  axisMax: number
  recommendedChannel: string
  width?: number
  depth?: number
  height?: number
  labelColor: string
}

/**
 * The names of the channels.
 *
 * They are drawn as real text in the page rather than as three-dimensional
 * type, because three-dimensional type costs a hundred kilobytes and
 * because real text is the part a screen reader can read.
 */
export function ChannelLabels({
  channels,
  axisMin,
  axisMax,
  recommendedChannel,
  width = 10,
  depth = 6,
  height = 2.2,
  labelColor,
}: ChannelLabelsProps) {
  const span = axisMax - axisMin || 1
  const rowSpacing = channels.length > 1 ? depth / (channels.length - 1) : 0

  return (
    <>
      {channels.map((channel, row) => {
        // Only the part of the distribution inside the axis is drawn, so
        // only that part is labelled.
        const bins = channel.bins.filter((bin) => bin.x >= axisMin && bin.x <= axisMax)
        if (bins.length === 0) return null

        // Each channel is scaled to its own peak, as the surface is.
        let peak = 0
        for (const bin of bins) {
          if (bin.density > peak) peak = bin.density
        }
        if (peak <= 0) peak = 1

        const top = bins.reduce((best, bin) => (bin.density > best.density ? bin : best))
        const x = ((top.x - axisMin) / span - 0.5) * width
        const y = (row - (channels.length - 1) / 2) * rowSpacing
        const isRecommended = channel.channel === recommendedChannel

        return (
          <Html
            key={channel.channel}
            position={[x, y, (top.density / peak) * height + 0.18]}
            center
            zIndexRange={[10, 0]}
            style={{ pointerEvents: 'none' }}
          >
            <span
              className="whitespace-nowrap rounded-full border border-border px-2 py-0.5 text-[11px] font-medium"
              style={{
                background: 'rgb(var(--popover))',
                color: isRecommended ? 'rgb(var(--primary))' : labelColor,
                borderColor: isRecommended ? 'rgb(var(--primary))' : 'rgb(var(--border))',
              }}
            >
              {channelShortLabel(channel.channel)}
            </span>
          </Html>
        )
      })}
    </>
  )
}
