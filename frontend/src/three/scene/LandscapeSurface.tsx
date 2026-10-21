import * as THREE from 'three'
import type { ChannelDistribution } from '@/types/distribution'

export interface LandscapeSurfaceProps {
  /** The geometry of the ridges, one per channel. */
  geometries: THREE.BufferGeometry[]
  /** The channels that are drawn, in order. */
  channels: ChannelDistribution[]
}

/**
 * The landscape.
 *
 * One ridge per channel. The geometry is built by a pure function, so
 * that the shape can be checked without a graphics context.
 */
export function LandscapeSurface({ geometries, channels }: LandscapeSurfaceProps) {
  if (geometries.length === 0) return null

  return (
    <group>
      {geometries.map((geometry, index) => (
        <mesh key={channels[index]?.channel ?? index} geometry={geometry}>
          {/*
            The material is unlit on purpose. The colour of a ridge is the
            token of the theme, and a lit material would turn it into
            something else. The form comes from the shading baked into the
            vertices and from the outline, not from a light.
          */}
          <meshBasicMaterial
            vertexColors
            side={THREE.DoubleSide}
            transparent
            opacity={0.9}
          />
        </mesh>
      ))}
    </group>
  )
}
