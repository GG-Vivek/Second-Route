import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChannelLandscape } from '@/components/decision/ChannelLandscape'
import { ChannelLandscape2D } from '@/components/decision/ChannelLandscape2D'
import { buildSurfaceGeometries } from '@/three/scene/surfaceGeometry'
import { supportsWebGL } from '@/three/webgl'
import type { ChannelDistribution, DecisionDistribution } from '@/types/distribution'

function channel(
  name: string,
  density: number[],
  overrides: Partial<ChannelDistribution> = {}
): ChannelDistribution {
  // The percentiles follow the bins, so that the fixture is a
  // distribution rather than a set of unrelated numbers.
  const bins = density.map((d, index) => ({ x: index * 100, density: d }))
  return {
    channel: name,
    eligible: true,
    exclusion_reason: null,
    mean: 200,
    stddev: 100,
    p10: bins[0]?.x ?? 0,
    p50: bins[Math.floor(bins.length / 2)]?.x ?? 0,
    p90: bins[bins.length - 1]?.x ?? 0,
    probability_best: 0.5,
    bins,
    ...overrides,
  }
}

const DISTRIBUTION: DecisionDistribution = {
  decision_id: 'decision-1',
  input_snapshot_hash: 'abc123',
  model_version: 'decision-v1',
  risk_profile: 'balanced',
  recommended_channel: 'RESELL_OPEN_BOX',
  confidence: 0.86,
  matches_stored_decision: true,
  bin_count: 5,
  axis: { min: 0, max: 40 },
  channels: [
    channel('RESELL_OPEN_BOX', [0, 0.2, 0.5, 0.2, 0]),
    channel('RESELL_REFURB', [0, 0.1, 0.3, 0.1, 0]),
    channel('RECYCLE', [0.4, 0.4, 0.1, 0, 0]),
  ],
}

describe('the WebGL probe', () => {
  it('says no when the browser has no WebGL', () => {
    // jsdom has no WebGL, which is exactly the case the probe exists for.
    expect(supportsWebGL()).toBe(false)
  })
})

describe('the flat landscape', () => {
  it('draws a curve for every eligible channel', () => {
    render(
      <ChannelLandscape2D
        distribution={DISTRIBUTION}
        recommendedChannel="RESELL_OPEN_BOX"
      />,
    )

    expect(screen.getByTestId('landscape-curve-RESELL_OPEN_BOX')).toBeInTheDocument()
    expect(screen.getByTestId('landscape-curve-RESELL_REFURB')).toBeInTheDocument()
    expect(screen.getByTestId('landscape-curve-RECYCLE')).toBeInTheDocument()
  })

  it('leaves out the channels that could not be used', () => {
    const withExcluded: DecisionDistribution = {
      ...DISTRIBUTION,
      channels: [
        ...DISTRIBUTION.channels,
        channel('HOLD', [], { eligible: false, exclusion_reason: 'Not now' }),
      ],
    }

    render(
      <ChannelLandscape2D
        distribution={withExcluded}
        recommendedChannel="RESELL_OPEN_BOX"
      />,
    )

    expect(screen.queryByTestId('landscape-curve-HOLD')).not.toBeInTheDocument()
  })

  it('names every channel it draws', () => {
    render(
      <ChannelLandscape2D
        distribution={DISTRIBUTION}
        recommendedChannel="RESELL_OPEN_BOX"
      />,
    )

    expect(screen.getByText('Open-box')).toBeInTheDocument()
    expect(screen.getByText('Refurbish')).toBeInTheDocument()
    expect(screen.getByText('Recycle')).toBeInTheDocument()
  })

  it('marks the marks of the recommended channel', () => {
    render(
      <ChannelLandscape2D
        distribution={DISTRIBUTION}
        recommendedChannel="RESELL_OPEN_BOX"
      />,
    )

    expect(screen.getByText('$0.00')).toBeInTheDocument()
    expect(screen.getByText('$200.00')).toBeInTheDocument()
    expect(screen.getByText('$400.00')).toBeInTheDocument()
  })

  it('describes itself for a screen reader', () => {
    render(
      <ChannelLandscape2D
        distribution={DISTRIBUTION}
        recommendedChannel="RESELL_OPEN_BOX"
      />,
    )

    const image = screen.getByRole('img')
    expect(image).toHaveAccessibleName(/distribution of the net value/i)
  })
})

describe('the landscape switch', () => {
  it('draws flat when the browser has no WebGL', () => {
    render(
      <ChannelLandscape
        distribution={DISTRIBUTION}
        recommendedChannel="RESELL_OPEN_BOX"
      />,
    )

    expect(screen.getByTestId('channel-landscape-2d')).toBeInTheDocument()
    expect(screen.getByTestId('landscape-flat')).toHaveAttribute('aria-pressed', 'true')
  })

  it('will not offer three dimensions when the browser cannot draw them', () => {
    render(
      <ChannelLandscape
        distribution={DISTRIBUTION}
        recommendedChannel="RESELL_OPEN_BOX"
      />,
    )

    expect(screen.getByTestId('landscape-spatial')).toBeDisabled()
  })

  it('says why it is drawing flat', () => {
    render(
      <ChannelLandscape
        distribution={DISTRIBUTION}
        recommendedChannel="RESELL_OPEN_BOX"
      />,
    )

    expect(
      screen.getByText(/cannot draw in three dimensions/i)
    ).toBeInTheDocument()
  })

  it('switches between the two drawings', async () => {
    render(
      <ChannelLandscape
        distribution={DISTRIBUTION}
        recommendedChannel="RESELL_OPEN_BOX"
      />,
    )

    await userEvent.click(screen.getByTestId('landscape-flat'))
    expect(screen.getByTestId('landscape-flat')).toHaveAttribute('aria-pressed', 'true')
  })
})

describe('the surface geometry', () => {
  const input = {
    channels: [
      channel('RESELL_OPEN_BOX', [0, 0.5, 1, 0.5, 0]),
      channel('RECYCLE', [1, 0.5, 0, 0, 0]),
    ],
    axisMin: 0,
    axisMax: 400,
    recommendedChannel: 'RESELL_OPEN_BOX',
    width: 10,
    depth: 6,
    height: 2,
    recommendedColor: 'rgb(200, 242, 64)',
    otherColor: 'rgb(198, 200, 184)',
  }

  it('builds one ridge per channel', () => {
    expect(buildSurfaceGeometries(input)).toHaveLength(2)
  })

  it('has two vertices per column, the top of the ridge and its foot', () => {
    const geometries = buildSurfaceGeometries(input)
    expect(geometries[0].getAttribute('position').count).toBe(5 * 2)
  })

  it('joins the vertices into a curtain', () => {
    const geometries = buildSurfaceGeometries(input)
    // Two triangles per gap between columns.
    expect(geometries[0].getIndex()?.count).toBe((5 - 1) * 6)
  })

  it('scales each ridge against its own peak', () => {
    const geometries = buildSurfaceGeometries(input)
    const position = geometries[0].getAttribute('position')

    let highest = -Infinity
    for (let index = 2; index < position.array.length; index += 3) {
      highest = Math.max(highest, position.array[index])
    }
    expect(highest).toBeCloseTo(2)
  })

  it('hangs every ridge from the same floor', () => {
    for (const geometry of buildSurfaceGeometries(input)) {
      const position = geometry.getAttribute('position')
      // The foot of the ridge is the second vertex of each column.
      for (let index = 5; index < position.array.length; index += 6) {
        expect(position.array[index]).toBeCloseTo(0)
      }
    }
  })

  it('puts the channels into the distance', () => {
    const geometries = buildSurfaceGeometries(input)
    const first = geometries[0].getAttribute('position')
    const second = geometries[1].getAttribute('position')
    expect(first.getY(0)).toBeLessThan(second.getY(0))
  })

  it('colours the recommended channel differently', () => {
    const geometries = buildSurfaceGeometries(input)
    const color = geometries[0].getAttribute('color')
    const other = geometries[1].getAttribute('color')
    expect([color.getX(0), color.getY(0), color.getZ(0)]).not.toEqual([
      other.getX(0),
      other.getY(0),
      other.getZ(0),
    ])
  })

  it('always gives the same geometry', () => {
    const first = buildSurfaceGeometries(input)
    const second = buildSurfaceGeometries(input)
    expect(Array.from(first[0].getAttribute('position').array)).toEqual(
      Array.from(second[0].getAttribute('position').array)
    )
  })

  it('gives no geometry when there is nothing to draw', () => {
    expect(buildSurfaceGeometries({ ...input, channels: [] })).toHaveLength(0)
  })
})
