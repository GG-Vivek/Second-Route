import { OrbitControls } from '@react-three/drei'
import { useMemo } from 'react'
import type { ChannelDistribution } from '@/types/distribution'
import { ChannelLabels } from './ChannelLabels'
import { FrameCamera } from './FrameCamera'
import { LandscapeSurface } from './LandscapeSurface'
import { buildSurfaceGeometries } from './surfaceGeometry'

export interface LandscapeSceneProps {
  /** The channels that are drawn. */
  channels: ChannelDistribution[]
  axisMin: number
  axisMax: number
  recommendedChannel: string
  /** The hue each series carries, by its position (F11.8). */
  colorFor: (channel: string, index: number) => string
  gridColor: string
  floorColor: string
  labelColor: string
}

/** How wide the landscape is, in world units. */
const WIDTH = 9
/** How tall the tallest ridge is. */
const HEIGHT = 2.2
/** How far apart two channels are. */
const CHANNEL_SPACING = 1.6

/**
 * The landscape scene.
 *
 * The material is unlit, so the colour of a ridge is the colour of the
 * token and not something the light has made up. There is no environment
 * map, because the pmndrs one is fetched from a CDN at render time and
 * this application has to work with no network at all.
 */
export function LandscapeScene({
  channels,
  axisMin,
  axisMax,
  recommendedChannel,
  colorFor,
  gridColor,
  floorColor,
  labelColor,
}: LandscapeSceneProps) {
  // The depth follows the number of channels, so that the ridges are
  // always the same distance apart however many there are.
  const depth = Math.max(CHANNEL_SPACING, (channels.length - 1) * CHANNEL_SPACING)

  // The camera and the orbit controls have to agree on what they are
  // looking at, or the two of them fight over the framing on every frame.
  const target: [number, number, number] = [0, 0, HEIGHT * 0.4]

  const geometries = useMemo(
    () =>
      buildSurfaceGeometries({
        channels,
        axisMin,
        axisMax,
        width: WIDTH,
        depth,
        height: HEIGHT,
        colorFor,
      }),
    [channels, axisMin, axisMax, depth, colorFor]
  )

  const gridLines = useMemo(() => {
    const lines: number[] = []
    const half = WIDTH / 2
    const depthHalf = depth / 2
    // The floor grid, drawn as line segments.
    for (let i = -4; i <= 4; i++) {
      lines.push(i * (WIDTH / 8), 0, -depthHalf, i * (WIDTH / 8), 0, depthHalf)
    }
    for (let i = -3; i <= 3; i++) {
      lines.push(-half, 0, i * (depth / 6), half, 0, i * (depth / 6))
    }
    return new Float32Array(lines)
  }, [depth])

  return (
    <>
      <FrameCamera geometries={geometries} target={target} />

      <LandscapeSurface geometries={geometries} channels={channels} />

      {/* The floor itself, so the ridges stand on a ground rather than on
          the void. It is unlit and slightly translucent: a plate of the
          page's own muted surface, not a lit object with an opinion. It
          paints before the ridges rather than by distance, because a
          translucent plane that is wider than it is deep otherwise sorts
          in front of the ridge whose foot it should be behind. */}
      <mesh position={[0, 0, -0.004]} renderOrder={-1}>
        <planeGeometry args={[WIDTH, depth + 0.6]} />
        <meshBasicMaterial
          color={floorColor}
          transparent
          opacity={0.6}
          depthWrite={false}
        />
      </mesh>

      {/* The floor, with a grid that fades into the distance. */}
      <lineSegments position={[0, 0, -0.001]}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[gridLines, 3]}
            count={gridLines.length / 3}
            array={gridLines}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color={gridColor} transparent opacity={0.28} />
      </lineSegments>

      <ChannelLabels
        channels={channels}
        axisMin={axisMin}
        axisMax={axisMax}
        recommendedChannel={recommendedChannel}
        width={WIDTH}
        depth={depth}
        height={HEIGHT}
        labelColor={labelColor}
      />

      <OrbitControls
        makeDefault
        enablePan={false}
        enableDamping
        dampingFactor={0.08}
        minPolarAngle={Math.PI * 0.12}
        maxPolarAngle={Math.PI * 0.45}
        minZoom={20}
        maxZoom={400}
        target={target}
      />
    </>
  )
}
