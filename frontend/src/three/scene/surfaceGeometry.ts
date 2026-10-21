import * as THREE from 'three'
import type { ChannelDistribution } from '@/types/distribution'

export interface SurfaceGeometryInput {
  /** The channels that are drawn, in order. */
  channels: ChannelDistribution[]
  /** The left end of the shared axis. */
  axisMin: number
  /** The right end of the shared axis. */
  axisMax: number
  /** The channel the engine recommended. */
  recommendedChannel: string
  /** How wide the landscape is, in world units. */
  width: number
  /** How deep it is, from the first channel to the last. */
  depth: number
  /** How tall the tallest ridge is. */
  height: number
  /** The colour of the recommended channel. */
  recommendedColor: string
  /** The colour of the other channels. */
  otherColor: string
}

/** How dark the foot of a ridge is, relative to its colour. */
const BASE_SHADE = 0.72

/**
 * Build the geometry of the landscape.
 *
 * One ridge per channel: a curtain hanging from the curve down to the
 * floor. The ridges are separate pieces rather than one continuous sheet,
 * because a sheet joins the channels to each other and a tall channel
 * next to a flat one would then be joined by a wall.
 *
 * Each ridge is scaled to its own peak rather than to the tallest of them
 * all. A channel with a narrow spread has a high peak and a wide channel
 * has a low one, so a shared scale would flatten the channels that matter
 * into nothing.
 *
 * The colour fades from the foot of the ridge to its top, so that the
 * shape reads without the light having to do all the work.
 *
 * The function is pure: the same input always gives the same geometry.
 */
export function buildSurfaceGeometries({
  channels,
  axisMin,
  axisMax,
  recommendedChannel,
  width,
  depth,
  height,
  recommendedColor,
  otherColor,
}: SurfaceGeometryInput): THREE.BufferGeometry[] {
  const span = axisMax - axisMin || 1
  const rowSpacing = channels.length > 1 ? depth / (channels.length - 1) : 0

  const geometries: THREE.BufferGeometry[] = []

  channels.forEach((channel, row) => {
    // Only the part of the distribution that falls inside the axis is
    // drawn. A channel whose whole range is outside it has nothing to
    // say about the decision and is left out.
    const bins = channel.bins.filter((bin) => bin.x >= axisMin && bin.x <= axisMax)
    if (bins.length < 2) return

    let peak = 0
    for (const bin of bins) {
      if (bin.density > peak) peak = bin.density
    }
    if (peak <= 0) peak = 1

    const colour = new THREE.Color(
      channel.channel === recommendedChannel ? recommendedColor : otherColor
    )
    const y = (row - (channels.length - 1) / 2) * rowSpacing

    // Two vertices per column: the top of the ridge and its foot.
    const cols = bins.length
    const positions = new Float32Array(cols * 2 * 3)
    const colors = new Float32Array(cols * 2 * 3)
    const indices: number[] = []

    for (let col = 0; col < cols; col++) {
      const bin = bins[col]
      const x = ((bin.x - axisMin) / span - 0.5) * width
      const z = (bin.density / peak) * height

      const shade = BASE_SHADE + (1 - BASE_SHADE) * (bin.density / peak)

      const top = col * 2 * 3
      positions[top] = x
      positions[top + 1] = y
      positions[top + 2] = z
      colors[top] = colour.r * shade
      colors[top + 1] = colour.g * shade
      colors[top + 2] = colour.b * shade

      const foot = (col * 2 + 1) * 3
      positions[foot] = x
      positions[foot + 1] = y
      positions[foot + 2] = 0
      colors[foot] = colour.r * BASE_SHADE
      colors[foot + 1] = colour.g * BASE_SHADE
      colors[foot + 2] = colour.b * BASE_SHADE
    }

    for (let col = 0; col < cols - 1; col++) {
      const top0 = col * 2
      const foot0 = col * 2 + 1
      const top1 = (col + 1) * 2
      const foot1 = (col + 1) * 2 + 1
      indices.push(top0, foot0, top1, foot0, foot1, top1)
    }

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geometry.setIndex(indices)
    geometry.computeVertexNormals()
    geometries.push(geometry)
  })

  return geometries
}
