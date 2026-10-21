// Types for the decision distribution (F8.4).
//
// The distribution is the engine's own Monte Carlo output, replayed from
// the stored snapshot and binned into a density histogram. Every channel
// is drawn against the same axis, so that two channels can be compared.

export interface DensityBin {
  /** The middle of the bar, in the units of the net value. */
  x: number
  /** The probability density at that point. */
  density: number
}

export interface ChannelDistribution {
  channel: string
  eligible: boolean
  exclusion_reason: string | null
  mean: number
  stddev: number
  p10: number
  p50: number
  p90: number
  probability_best: number
  /** Empty for a channel that could not be used. */
  bins: DensityBin[]
}

export interface DistributionAxis {
  min: number
  max: number
}

export interface DecisionDistribution {
  decision_id: string
  input_snapshot_hash: string
  model_version: string
  risk_profile: string
  recommended_channel: string
  confidence: number
  /**
   * Whether the replay still recommends the same channel with the same
   * confidence as the stored decision. It is false when the price data
   * has moved since the decision was made.
   */
  matches_stored_decision: boolean
  bin_count: number
  axis: DistributionAxis
  channels: ChannelDistribution[]
}

/**
 * The density of one channel at one point of the axis.
 *
 * The helper exists so that the drawing code does not have to deal with
 * a channel that has no bars.
 */
export function densityAt(channel: ChannelDistribution, x: number): number {
  if (channel.bins.length === 0) return 0
  let closest = channel.bins[0]
  for (const bin of channel.bins) {
    if (Math.abs(bin.x - x) < Math.abs(closest.x - x)) closest = bin
  }
  return closest.density
}

/**
 * The peak density of a channel.
 *
 * The height of the tallest bar, which is what the three-dimensional view
 * scales against.
 */
export function peakDensity(channels: ChannelDistribution[]): number {
  let peak = 0
  for (const channel of channels) {
    for (const bin of channel.bins) {
      if (bin.density > peak) peak = bin.density
    }
  }
  return peak
}

/**
 * The channels the decision is actually made between.
 *
 * The engine evaluates every channel, including the ones that recover
 * almost nothing. The confidence depends on the channels whose net values
 * could have been chosen instead, which are the ones whose range overlaps
 * the recommendation's range. The rest are not part of the decision.
 */
export function decisionChannels(
  distribution: DecisionDistribution,
  rivals = 2,
): ChannelDistribution[] {
  const eligible = distribution.channels.filter(
    (channel) => channel.eligible && channel.bins.length > 0
  )
  const recommended = eligible.find(
    (channel) => channel.channel === distribution.recommended_channel
  )
  if (!recommended) return eligible

  const overlapping = eligible
    .filter(
      (channel) =>
        channel.channel !== recommended.channel &&
        channel.p90 >= recommended.p10 &&
        channel.p10 <= recommended.p90
    )
    .sort((a, b) => Math.abs(a.mean - recommended.mean) - Math.abs(b.mean - recommended.mean))
    .slice(0, rivals)

  return [recommended, ...overlapping]
}

/**
 * The range of the axis that the decision is made in.
 *
 * Drawn on one axis, the channels that recover nothing squeeze the
 * channels that matter into a corner of the picture. The landscape is
 * drawn over the range that the decision is made in instead, and the
 * table of alternatives carries the numbers for every channel.
 */
export function focusAxis(
  distribution: DecisionDistribution,
  rivals = 2,
): { min: number; max: number } {
  const focus = decisionChannels(distribution, rivals)
  if (focus.length === 0) return distribution.axis

  let min = Infinity
  let max = -Infinity
  for (const channel of focus) {
    min = Math.min(min, channel.p10)
    max = Math.max(max, channel.p90)
  }

  const padding = Math.max((max - min) * 0.1, 10)
  return { min: min - padding, max: max + padding }
}
