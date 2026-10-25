import { Canvas } from '@react-three/fiber'
import { HeroPrismScene } from './scene/HeroPrismScene'
import { useLandscapeColors } from './useThemeColors'

export interface HeroPrismCanvasProps {
  activeChannel: string
  onSelectChannel?: (channel: string) => void
}

/**
 * The 3D disposition visualizer in the landing page hero.
 *
 * Rendered using react-three-fiber, with smooth floating motion and cursor
 * tilt tracking. Dynamically imported so the Three.js runtime is deferred.
 */
export default function HeroPrismCanvas({
  activeChannel,
  onSelectChannel,
}: HeroPrismCanvasProps) {
  const colors = useLandscapeColors()

  return (
    <Canvas
      camera={{ position: [0, 0, 7.2], fov: 38 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true }}
      className="size-full"
      aria-label="3D Disposition Hologram"
    >
      <HeroPrismScene
        colors={colors}
        activeChannel={activeChannel}
        onSelectChannel={onSelectChannel}
      />
    </Canvas>
  )
}
