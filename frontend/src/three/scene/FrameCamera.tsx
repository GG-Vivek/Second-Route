import { useEffect } from 'react'
import { useThree } from '@react-three/fiber'
import * as THREE from 'three'

export interface FrameCameraProps {
  /** The geometry of the landscape, which is what has to fit. */
  geometries: THREE.BufferGeometry[]
  /** What the orbit controls look at. */
  target: [number, number, number]
  /** The elevation the camera looks down from. */
  elevation?: number
}

/**
 * Put the camera where the landscape fits.
 *
 * The projection is orthographic, and that is a deliberate choice. This is
 * a picture of data, not a photograph of a place: a perspective lens would
 * make the far ridges smaller than the near ones, and the reader would be
 * comparing the size of a ridge with how far away it is rather than with
 * the shape of the distribution it stands for.
 *
 * The zoom is worked out from the geometry itself rather than from a
 * formula about how big the scene was meant to be. The shape of the
 * distributions decides how tall the ridges are and how far apart they
 * are, and the camera has to follow that rather than an assumption about
 * it. Anything that would fall outside the frame is therefore impossible.
 */
export function FrameCamera({
  geometries,
  target,
  elevation = 0.72,
}: FrameCameraProps) {
  const { camera, size } = useThree()

  useEffect(() => {
    const orthographic = camera as THREE.OrthographicCamera
    if (!orthographic.isOrthographicCamera) return
    if (geometries.length === 0) return

    const sin = Math.sin(elevation)
    const cos = Math.cos(elevation)

    const lookAt = new THREE.Vector3(target[0], target[1], target[2])
    const direction = new THREE.Vector3(0, -sin, cos).normalize()

    orthographic.position.copy(lookAt).add(direction.multiplyScalar(60))
    orthographic.lookAt(lookAt)
    orthographic.updateMatrixWorld(true)

    // The corners of everything that has to be seen, in camera space.
    const box = new THREE.Box3()
    for (const geometry of geometries) {
      if (!geometry.boundingBox) geometry.computeBoundingBox()
      if (geometry.boundingBox) box.union(geometry.boundingBox)
    }
    if (box.isEmpty()) return

    let minX = Infinity
    let maxX = -Infinity
    let minY = Infinity
    let maxY = -Infinity

    const corner = new THREE.Vector3()
    for (const x of [box.min.x, box.max.x]) {
      for (const y of [box.min.y, box.max.y]) {
        for (const z of [box.min.z, box.max.z]) {
          corner.set(x, y, z).applyMatrix4(orthographic.matrixWorldInverse)
          minX = Math.min(minX, corner.x)
          maxX = Math.max(maxX, corner.x)
          minY = Math.min(minY, corner.y)
          maxY = Math.max(maxY, corner.y)
        }
      }
    }

    const halfWidth = Math.max((maxX - minX) / 2, 0.001)
    const halfHeight = Math.max((maxY - minY) / 2, 0.001)

    // The orthographic frustum is in pixels, so the zoom is what decides
    // how much of the world the canvas shows.
    const zoom = Math.min(size.width / (halfWidth * 2), size.height / (halfHeight * 2)) * 0.82
    orthographic.zoom = zoom

    // Move the camera so that the middle of the landscape is the middle of
    // the canvas.
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(orthographic.quaternion)
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(orthographic.quaternion)
    orthographic.position
      .add(right.multiplyScalar((minX + maxX) / 2))
      .add(up.multiplyScalar((minY + maxY) / 2))

    orthographic.updateMatrixWorld(true)
    orthographic.updateProjectionMatrix()
  }, [camera, size, geometries, target, elevation])

  return null
}
