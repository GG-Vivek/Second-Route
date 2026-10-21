/**
 * The WebGL support probe.
 *
 * react-three-fiber catches a failure to create a WebGL context in an
 * internal error boundary and renders nothing, without logging anything.
 * That is a silent failure, which the working rules forbid, so the
 * application checks for WebGL itself before it mounts a canvas.
 *
 * The probe is a pure function of the environment and is safe to call
 * from anywhere. It never leaves a context behind.
 */

/**
 * Whether this browser can render WebGL.
 *
 * The check for the constructor is deliberate: in an environment without
 * WebGL, asking a canvas for a context is either an error or noise, and
 * the answer is already known from the constructor.
 */
export function supportsWebGL(): boolean {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return false
  }

  const hasConstructor =
    typeof window.WebGLRenderingContext !== 'undefined' ||
    typeof window.WebGL2RenderingContext !== 'undefined'

  if (!hasConstructor) {
    return false
  }

  try {
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('webgl2') ?? canvas.getContext('webgl')
    if (!context) return false

    // Hand the context back rather than holding it for the life of the
    // page. Browsers have a small, fixed number of them.
    const lose = context.getExtension('WEBGL_lose_context')
    lose?.loseContext()

    return true
  } catch {
    return false
  }
}
