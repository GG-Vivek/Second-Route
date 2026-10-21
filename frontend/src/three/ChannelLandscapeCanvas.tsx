import { Canvas } from '@react-three/fiber'
import { useMemo } from 'react'
import type { DecisionDistribution } from '@/types/distribution'
import { decisionChannels, focusAxis } from '@/types/distribution'
import { LandscapeScene } from './scene/LandscapeScene'
import { useLandscapeColors } from './useThemeColors'

export interface ChannelLandscapeCanvasProps {
  distribution: DecisionDistribution
  recommendedChannel: string
}

/**
 * The three-dimensional landscape.
 *
 * This module is only ever reached through a dynamic import, so that the
 * three.js bundle is not part of the page that loads first. Everything
 * three-dimensional lives under `src/three/` and nowhere else.
 */
export default function ChannelLandscapeCanvas({
  distribution,
  recommendedChannel,
}: ChannelLandscapeCanvasProps) {
  const colors = useLandscapeColors()

  // The range the decision is made in, and the channels that fall in it.
  const axis = useMemo(() => focusAxis(distribution), [distribution])

  const channels = useMemo(
    () =>
      decisionChannels(distribution).filter((channel) =>
        channel.bins.some((bin) => bin.x >= axis.min && bin.x <= axis.max)
      ),
    [distribution, axis.min, axis.max]
  )

  if (channels.length === 0) return null

  return (
    <Canvas
      orthographic
      camera={{ position: [0, -12, 9], zoom: 40, near: 0.1, far: 200 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
      shadows="percentage"
      aria-label="The channel landscape"
      data-testid="channel-landscape-canvas"
    >
      <LandscapeScene
        channels={channels}
        axisMin={axis.min}
        axisMax={axis.max}
        recommendedChannel={recommendedChannel}
        recommendedColor={colors.recommended}
        otherColor={colors.other}
        gridColor={colors.grid}
        labelColor={colors.label}
      />
    </Canvas>
  )
}
