import { useEffect, useRef, useState } from 'react'
import { cn } from '@/utils/cn'

/**
 * An animated mesh gradient, drawn with a fragment shader (F11.5).
 *
 * The idea is the one in the shadergradient project: a few soft colour fields
 * drifting over a warm base, computed per pixel rather than painted. Here it is
 * written against plain WebGL, so it adds no dependency and it sits behind the
 * application's own tokens rather than a fixed set of colours.
 *
 * Three things a reader would notice are handled on purpose. A reader who
 * asks for reduced motion gets one still frame. A browser without WebGL gets a
 * CSS gradient with the same colours. The loop stops when the page is hidden,
 * so a background tab does not spend the battery.
 */

/** The two palettes. Each is four colours, from the base up to the highlights. */
const PALETTES: Record<'dark' | 'light', readonly [number, number, number][]> = {
  // The dark ink, lime, teal and a dull ochre, for the dark application.
  // The base is the background token itself, so the gradient and the surface
  // it sits behind are the same colour (ADR-008).
  dark: [
    [0.063, 0.11, 0.102],
    [0.42, 0.56, 0.1],
    [0.04, 0.3, 0.3],
    [0.32, 0.24, 0.14],
  ],
  // Warm off-white, pale lime, pale teal and sand, for the light one.
  light: [
    [0.99, 0.97, 0.95],
    [0.86, 0.95, 0.52],
    [0.7, 0.9, 0.86],
    [0.95, 0.88, 0.78],
  ],
}

/** The CSS gradient used where WebGL is not available. */
function fallbackGradient(palette: readonly [number, number, number][]): string {
  const [base, lime, teal, sand] = palette.map(
    ([r, g, b]) => `rgb(${Math.round(r * 255)} ${Math.round(g * 255)} ${Math.round(b * 255)})`,
  )
  return `radial-gradient(60% 50% at 20% 75%, ${lime} 0%, transparent 70%), radial-gradient(50% 60% at 80% 25%, ${teal} 0%, transparent 70%), radial-gradient(45% 45% at 55% 50%, ${sand} 0%, transparent 70%), ${base}`
}

const VERTEX_SHADER = `
attribute vec2 position;
void main() {
  gl_Position = vec4(position, 0.0, 1.0);
}
`

const FRAGMENT_SHADER = `
precision mediump float;
uniform vec2 resolution;
uniform float time;
uniform vec3 colours[4];

// A soft field: strong at the centre, gone by the radius.
float field(vec2 uv, vec2 centre, float radius) {
  vec2 d = uv - centre;
  return exp(-dot(d, d) / (radius * radius));
}

void main() {
  vec2 uv = gl_FragCoord.xy / resolution;
  float t = time * 0.12;

  vec2 a = vec2(0.22 + 0.16 * sin(t * 1.1), 0.72 + 0.12 * cos(t * 0.9));
  vec2 b = vec2(0.78 + 0.14 * cos(t * 0.8), 0.28 + 0.18 * sin(t * 1.3));
  vec2 c = vec2(0.50 + 0.24 * sin(t * 0.6 + 1.3), 0.50 + 0.20 * cos(t * 0.7));
  vec2 d = vec2(0.92 + 0.08 * sin(t * 1.7), 0.92 + 0.08 * cos(t * 1.2));

  vec3 colour = colours[0];
  colour = mix(colour, colours[1], 0.75 * field(uv, a, 0.48));
  colour = mix(colour, colours[2], 0.70 * field(uv, b, 0.52));
  colour = mix(colour, colours[3], 0.60 * field(uv, c, 0.42));
  colour = mix(colour, colours[1], 0.35 * field(uv, d, 0.30));

  // A little grain, so the gradient does not band on a good screen.
  float grain = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
  colour += (grain - 0.5) * 0.012;

  gl_FragColor = vec4(colour, 1.0);
}
`

function compile(gl: WebGLRenderingContext, type: number, source: string): WebGLShader | null {
  const shader = gl.createShader(type)
  if (!shader) return null
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    gl.deleteShader(shader)
    return null
  }
  return shader
}

export interface ShaderBackdropProps {
  /** Which palette to draw in. Follow the application's theme. */
  palette?: 'dark' | 'light'
  className?: string
}

/**
 * The backdrop itself. It fills its positioned parent.
 *
 * The parent has to be positioned (`relative`), and the backdrop is absolutely
 * placed behind the content with `aria-hidden`, so it never reaches a reader.
 */
export function ShaderBackdrop({ palette = 'dark', className }: ShaderBackdropProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [unsupported, setUnsupported] = useState(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const gl = canvas.getContext('webgl', { antialias: false, alpha: false })
    if (!gl) {
      setUnsupported(true)
      return
    }

    const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER)
    const fragment = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER)
    const program = gl.createProgram()
    if (!vertex || !fragment || !program) {
      setUnsupported(true)
      return
    }
    gl.attachShader(program, vertex)
    gl.attachShader(program, fragment)
    gl.linkProgram(program)
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      setUnsupported(true)
      return
    }
    gl.useProgram(program)

    // One triangle that covers the whole clip space.
    const buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
    const position = gl.getAttribLocation(program, 'position')
    gl.enableVertexAttribArray(position)
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0)

    const resolutionLocation = gl.getUniformLocation(program, 'resolution')
    const timeLocation = gl.getUniformLocation(program, 'time')
    const coloursLocation = gl.getUniformLocation(program, 'colours')
    gl.uniform3fv(coloursLocation, PALETTES[palette].flat())

    const resize = () => {
      // A high pixel density costs a great deal for a soft gradient, and
      // gains nothing visible, so the density is capped.
      const density = Math.min(window.devicePixelRatio || 1, 1.5)
      const box = canvas.getBoundingClientRect()
      canvas.width = Math.max(1, Math.round(box.width * density))
      canvas.height = Math.max(1, Math.round(box.height * density))
      gl.viewport(0, 0, canvas.width, canvas.height)
      gl.uniform2f(resolutionLocation, canvas.width, canvas.height)
    }

    const draw = (milliseconds: number) => {
      gl.uniform1f(timeLocation, milliseconds / 1000)
      gl.drawArrays(gl.TRIANGLES, 0, 3)
    }

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    let frame = 0
    const loop = (now: number) => {
      draw(now)
      frame = requestAnimationFrame(loop)
    }

    const observer = new ResizeObserver(() => {
      resize()
      if (reduceMotion) draw(0)
    })
    observer.observe(canvas)
    resize()

    if (reduceMotion) {
      draw(0)
    } else {
      frame = requestAnimationFrame(loop)
    }

    const pause = () => {
      cancelAnimationFrame(frame)
      frame = 0
    }
    const resume = () => {
      if (!reduceMotion && document.visibilityState === 'visible' && frame === 0) {
        frame = requestAnimationFrame(loop)
      }
    }
    const onVisibility = () => (document.visibilityState === 'visible' ? resume() : pause())
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      pause()
      observer.disconnect()
      gl.getExtension('WEBGL_lose_context')?.loseContext()
    }
  }, [palette])

  if (unsupported) {
    return (
      <div
        aria-hidden="true"
        data-testid="shader-fallback"
        className={cn('pointer-events-none absolute inset-0', className)}
        style={{ background: fallbackGradient(PALETTES[palette]) }}
      />
    )
  }

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      data-testid="shader-canvas"
      className={cn('pointer-events-none absolute inset-0 size-full', className)}
    />
  )
}
