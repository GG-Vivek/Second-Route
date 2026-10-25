import { Canvas } from '@react-three/fiber'
import { useCallback, useMemo } from 'react'
import { seriesHue } from '@/theme/meaning'
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

  // Which hue this channel carries — the same rule the flat drawing uses
  // (F11.8), asked of the three tokens this canvas read off the document.
  const colorFor = useCallback(
    (channel: string, index: number) =>
      colors.series[seriesHue(index, channel === recommendedChannel)],
    [colors.series, recommendedChannel]
  )

  if (channels.length === 0) return null

  return (
    <Canvas
      orthographic
      camera={{
        position: [0, -12, 9],
        zoom: 40,
        near: 0.1,
        far: 200,
        // The scene stands its ridges up the z axis, so the camera has to
        // say so too. OrbitControls measures its polar angle from the
        // camera's own up, and with the default y it clamped every pose to
        // a view from straight above — the landscape became a flat plate
        // with two curves painted on it, and the framing this component
        // works out was thrown away on the next frame.
        up: [0, 0, 1],
      }}
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
        colorFor={colorFor}
        gridColor={colors.grid}
        floorColor={colors.floor}
        labelColor={colors.label}
      />
    </Canvas>
  )
}
