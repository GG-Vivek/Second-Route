import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Float, RoundedBox } from '@react-three/drei'
import * as THREE from 'three'
import type { LandscapeColors } from '../useThemeColors'

export interface HeroPrismSceneProps {
  colors: LandscapeColors
  activeChannel: string
  onSelectChannel?: (channel: string) => void
}

interface ChannelNode {
  name: string
  hue: 'lime' | 'teal' | 'cyan' | 'purple' | 'orange'
  angle: number
  yOffset: number
}

const CHANNELS: ChannelNode[] = [
  { name: 'Refurbish', hue: 'lime', angle: -0.4, yOffset: 0.6 },
  { name: 'Open-Box', hue: 'teal', angle: 0.8, yOffset: 1.1 },
  { name: 'Parts', hue: 'cyan', angle: 2.2, yOffset: 0.2 },
  { name: 'Vendor Return', hue: 'purple', angle: 3.5, yOffset: -0.8 },
  { name: 'Recycle', hue: 'orange', angle: 4.8, yOffset: -0.5 },
]

export function HeroPrismScene({
  colors,
  activeChannel,
  onSelectChannel,
}: HeroPrismSceneProps) {
  const groupRef = useRef<THREE.Group>(null)
  const deviceRef = useRef<THREE.Group>(null)

  // Silky smooth mouse tilt tracking (Theatre & R3F inspiration)
  useFrame((state) => {
    if (!groupRef.current) return
    const targetRotY = state.pointer.x * 0.45
    const targetRotX = -state.pointer.y * 0.35
    groupRef.current.rotation.y = THREE.MathUtils.lerp(
      groupRef.current.rotation.y,
      targetRotY,
      0.06,
    )
    groupRef.current.rotation.x = THREE.MathUtils.lerp(
      groupRef.current.rotation.x,
      targetRotX,
      0.06,
    )
  })

  const activeNode = CHANNELS.find((c) => c.name === activeChannel) ?? CHANNELS[0]
  const activeColor = colors.series[activeNode.hue]

  return (
    <>
      <ambientLight intensity={1.2} />
      <directionalLight position={[5, 8, 6]} intensity={1.4} />
      <directionalLight position={[-6, -4, -4]} intensity={0.6} />
      <pointLight position={[0, 0, 3]} intensity={0.8} color={activeColor} />

      <group ref={groupRef}>
        <Float speed={1.6} rotationIntensity={0.25} floatIntensity={0.35}>
          {/* Central inspected device prism */}
          <group ref={deviceRef}>
            {/* Chassis */}
            <RoundedBox args={[2.0, 3.8, 0.22]} radius={0.16} smoothness={4}>
              <meshStandardMaterial
                color="#0f1715"
                roughness={0.18}
                metalness={0.85}
              />
            </RoundedBox>

            {/* Glass screen with transmission/glow */}
            <RoundedBox
              args={[1.82, 3.56, 0.02]}
              position={[0, 0, 0.12]}
              radius={0.1}
              smoothness={2}
            >
              <meshBasicMaterial
                color={activeColor}
                transparent
                opacity={0.15}
              />
            </RoundedBox>

            {/* Reticle / optical inspection beam line */}
            <mesh position={[0, 0, 0.13]}>
              <planeGeometry args={[1.6, 0.03]} />
              <meshBasicMaterial color={activeColor} transparent opacity={0.8} />
            </mesh>

            {/* Inner scanner reticle circles */}
            <mesh position={[0, 0, 0.125]}>
              <ringGeometry args={[0.35, 0.38, 32]} />
              <meshBasicMaterial color={activeColor} transparent opacity={0.6} />
            </mesh>
          </group>

          {/* Orbital guidance rings */}
          <mesh rotation={[Math.PI / 3, 0.25, 0]}>
            <torusGeometry args={[2.8, 0.01, 16, 80]} />
            <meshBasicMaterial
              color={colors.series.teal}
              transparent
              opacity={0.35}
            />
          </mesh>

          <mesh rotation={[-Math.PI / 4, -0.3, 0.2]}>
            <torusGeometry args={[3.2, 0.008, 16, 80]} />
            <meshBasicMaterial
              color={colors.series.lime}
              transparent
              opacity={0.25}
            />
          </mesh>

          {/* 5 Channel nodes orbiting around the device */}
          {CHANNELS.map((channel) => {
            const isSelected = channel.name === activeChannel
            const nodeColor = colors.series[channel.hue]
            const radius = 2.7
            const x = Math.cos(channel.angle) * radius
            const y = channel.yOffset
            const z = Math.sin(channel.angle) * radius * 0.7

            return (
              <group
                key={channel.name}
                position={[x, y, z]}
                onClick={() => onSelectChannel?.(channel.name)}
              >
                {/* Channel beacon sphere */}
                <mesh>
                  <sphereGeometry args={[isSelected ? 0.18 : 0.12, 24, 24]} />
                  <meshBasicMaterial color={nodeColor} />
                </mesh>

                {/* Aura halo for active channel */}
                {isSelected && (
                  <mesh>
                    <sphereGeometry args={[0.3, 24, 24]} />
                    <meshBasicMaterial
                      color={nodeColor}
                      transparent
                      opacity={0.3}
                    />
                  </mesh>
                )}
              </group>
            )
          })}
        </Float>
      </group>
    </>
  )
}
