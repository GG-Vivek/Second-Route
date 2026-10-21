/**
 * The fixtures the visual suite runs against.
 *
 * The suite is hermetic: every API call is answered with a fixture, so a
 * screenshot never depends on what happens to be in the database, and the
 * suite runs without a backend at all.
 */

export const UNIT_ID = '11111111-1111-1111-1111-111111111111'
export const DECISION_ID = '22222222-2222-2222-2222-222222222222'

const SKU = {
  id: '33333333-3333-3333-3333-333333333333',
  family: 'MacBook Pro',
  model_name: 'M3 Pro',
  year: '2023',
  storage_gb: '512',
  ram_gb: '18',
  color: 'Space Gray',
  region: 'US',
  specs_json: {},
  source: 'manufacturer',
  as_of: '2024-01-15',
}

const UNIT = {
  id: UNIT_ID,
  org_id: '44444444-4444-4444-4444-444444444444',
  sku_id: SKU.id,
  serial: 'C02SECOND0001',
  received_at: '2026-10-20T09:15:00Z',
  return_reason_code: 'buyer_remorse',
  order_channel: 'online',
  status: 'decided',
  sku: SKU,
}

const INSPECTION = {
  id: '55555555-5555-5555-5555-555555555555',
  unit_id: UNIT_ID,
  inspector_id: null,
  created_at: '2026-10-20T10:00:00Z',
  battery_health_pct: '94',
  battery_cycles: '120',
  cosmetic_grade: 'A',
  functional_tests_json: {
    display: true,
    keyboard: true,
    ports: true,
    camera: true,
    audio: true,
    wifi: true,
    battery: true,
    boot: true,
  },
  activation_lock: 'none',
  accessories_json: { charger: true, cable: true, box: true },
  notes: 'Screen is clean. Two scuffs on the lid.',
}

const CANDIDATE = (channel: string, mean: number, probabilityBest: number) => ({
  channel,
  eligible: true,
  exclusion_reason: null,
  mean,
  stddev: 90,
  p10: mean - 200,
  p50: mean,
  p90: mean + 200,
  probability_best: probabilityBest,
  certainty_equivalent: mean - 40,
  grade_probabilities: { A: 0.8, B: 0.15, C: 0.04, D: 0.01 },
  price_sources: { [`${channel}:A`]: 'synthetic' },
  price_as_of: { [`${channel}:A`]: '2026-10-01T00:00:00' },
  breakdown: {
    sale_price: mean + 300,
    fees: 190,
    logistics: 28,
    handling: 18,
    repair: 15,
    holding: 2,
    total_cost: 253,
    net: mean,
  },
})

const DECISION = {
  id: DECISION_ID,
  unit_id: UNIT_ID,
  created_at: '2026-10-20T11:00:00Z',
  model_version: 'decision-v1',
  risk_profile: 'balanced',
  recommended_channel: 'RESELL_OPEN_BOX',
  confidence: 0.86,
  fallback_used: false,
  fallback_channel: null,
  candidates: [
    CANDIDATE('RESELL_OPEN_BOX', 1470, 0.82),
    CANDIDATE('RESELL_REFURB', 1090, 0.16),
    CANDIDATE('PARTS_HARVEST', -37, 0.01),
    CANDIDATE('RECYCLE', 79, 0.01),
    CANDIDATE('DONATE', -44, 0),
  ],
  reasons: [
    {
      code: 'favourable_sale_price',
      label: 'Expected sale price',
      contribution: 320,
      favours_recommended: true,
      text: 'Resell as open-box wins on expected sale price: $320.00 better than refurbish and resell.',
    },
    {
      code: 'repair_cost',
      label: 'Repair cost',
      contribution: 45,
      favours_recommended: true,
      text: 'Resell as open-box avoids $45.00 of repair that refurbish and resell needs.',
    },
  ],
  flip_conditions: [
    {
      input_name: 'channel_fee_pct',
      input_kind: 'numeric',
      current_value: 0.12,
      threshold_value: 0.28,
      new_channel: 'RESELL_REFURB',
      direction: 'above',
      description:
        'If platform fee were above 28.0% the recommendation would become refurbish and resell.',
      target_channel: 'RESELL_OPEN_BOX',
    },
  ],
  action_steps: [
    {
      order: 1,
      title: 'Wipe the device',
      detail: 'Factory-reset the device before it leaves the warehouse.',
      reference: 'NIST SP 800-88 Rev. 1',
    },
    {
      order: 2,
      title: 'Photograph four angles',
      detail: 'Front, back, both sides, and the serial.',
      reference: null,
    },
  ],
  data_freshness: {
    price_sources: {},
    price_as_of: {},
    cost_sources: {},
    cost_as_of: {},
    is_synthetic: true,
    warnings: ['Prices are synthetic. This is a prototype, not a money claim.'],
  },
  input_snapshot_hash: 'abc123',
  is_prototype: true,
  prototype_badge: 'Prototype - synthetic prices',
}

/** A density histogram with a bell shape, so the picture has a shape. */
function bell(center: number, spread: number, points = 96) {
  const bins = []
  for (let index = 0; index < points; index++) {
    const x = center + (index / (points - 1) - 0.5) * spread * 2
    bins.push({ x, density: Math.exp(-((x - center) ** 2) / (2 * (spread / 4) ** 2)) / 12 })
  }
  return bins
}

const DISTRIBUTION = {
  decision_id: DECISION_ID,
  input_snapshot_hash: 'abc123',
  model_version: 'decision-v1',
  risk_profile: 'balanced',
  recommended_channel: 'RESELL_OPEN_BOX',
  confidence: 0.86,
  matches_stored_decision: true,
  bin_count: 96,
  axis: { min: 300, max: 2100 },
  channels: [
    {
      channel: 'RESELL_OPEN_BOX',
      eligible: true,
      exclusion_reason: null,
      mean: 1470,
      stddev: 90,
      p10: 1189,
      p50: 1472,
      p90: 1752,
      probability_best: 0.82,
      bins: bell(1470, 400),
    },
    {
      channel: 'RESELL_REFURB',
      eligible: true,
      exclusion_reason: null,
      mean: 1090,
      stddev: 120,
      p10: 800,
      p50: 1093,
      p90: 1400,
      probability_best: 0.16,
      bins: bell(1090, 520),
    },
    {
      channel: 'RECYCLE',
      eligible: true,
      exclusion_reason: null,
      mean: 79,
      stddev: 60,
      p10: -20,
      p50: 79,
      p90: 180,
      probability_best: 0.01,
      bins: bell(79, 180),
    },
    {
      channel: 'DONATE',
      eligible: true,
      exclusion_reason: null,
      mean: -44,
      stddev: 30,
      p10: -100,
      p50: -44,
      p90: 10,
      probability_best: 0,
      bins: bell(-44, 120),
    },
    {
      channel: 'PARTS_HARVEST',
      eligible: true,
      exclusion_reason: null,
      mean: -37,
      stddev: 50,
      p10: -120,
      p50: -37,
      p90: 40,
      probability_best: 0.01,
      bins: bell(-37, 140),
    },
    {
      channel: 'HOLD',
      eligible: false,
      exclusion_reason: 'A launch is expected inside the hold window',
      mean: 0,
      stddev: 0,
      p10: 0,
      p50: 0,
      p90: 0,
      probability_best: 0,
      bins: [],
    },
  ],
}

const NORTH_STAR = {
  synthetic: {
    returns_count: 128,
    net_recovered_total: 190400,
    baseline_total: 96000,
    net_recovered_per_return: 1487.5,
    baseline_per_return: 750,
    above_baseline_per_return: 737.5,
    observed_baseline_count: 61,
    estimated_baseline_count: 67,
  },
  real: {
    returns_count: 0,
    net_recovered_total: 0,
    baseline_total: 0,
    net_recovered_per_return: 0,
    baseline_per_return: 0,
    above_baseline_per_return: 0,
    observed_baseline_count: 0,
    estimated_baseline_count: 0,
  },
  baseline_channel: 'RECYCLE',
}

const REGRET = {
  bucket: 'month',
  synthetic: [
    {
      period: '2026-08',
      count: 18,
      mean_regret: 142.5,
      observed_count: 9,
      estimated_count: 9,
      observed_mean_regret: 151,
      estimated_mean_regret: 133,
    },
    {
      period: '2026-09',
      count: 24,
      mean_regret: 118.2,
      observed_count: 14,
      estimated_count: 10,
      observed_mean_regret: 122,
      estimated_mean_regret: 112,
    },
    {
      period: '2026-10',
      count: 21,
      mean_regret: 96.4,
      observed_count: 12,
      estimated_count: 9,
      observed_mean_regret: 101,
      estimated_mean_regret: 89,
    },
  ],
  real: [],
}

const CALIBRATION = {
  bins: [
    { lower: 0, upper: 0.2, count: 3, mean_predicted: 0.1, observed_frequency: 0.07, gap: 0.03 },
    { lower: 0.2, upper: 0.4, count: 11, mean_predicted: 0.31, observed_frequency: 0.27, gap: 0.04 },
    { lower: 0.4, upper: 0.6, count: 19, mean_predicted: 0.5, observed_frequency: 0.53, gap: -0.03 },
    { lower: 0.6, upper: 0.8, count: 34, mean_predicted: 0.71, observed_frequency: 0.68, gap: 0.03 },
    { lower: 0.8, upper: 1, count: 61, mean_predicted: 0.9, observed_frequency: 0.93, gap: -0.03 },
  ],
  ece: 0.0341,
  sample_size: 128,
  bin_count: 5,
  active_version: 'calibration-v1',
}

const OVERRIDE_RATE = {
  synthetic: {
    decisions_count: 128,
    overrides_count: 26,
    override_rate: 0.2031,
    by_reason: [
      { reason: 'Too risky', count: 11, share: 0.423 },
      { reason: 'The customer asked', count: 8, share: 0.308 },
      { reason: 'The parts were worth more', count: 5, share: 0.192 },
      { reason: 'Wrong inspection', count: 2, share: 0.077 },
    ],
  },
  real: {
    decisions_count: 0,
    overrides_count: 0,
    override_rate: 0,
    by_reason: [],
  },
}

const SOURCE_HEALTH = [
  {
    source: 'synthetic',
    kind: 'price',
    status: 'fresh',
    last_update: '2026-10-20T08:00:00Z',
    age_hours: 27,
    error_count: 0,
    is_synthetic: true,
    stale_limit_hours: 48,
  },
  {
    source: 'ebay_active',
    kind: 'price',
    status: 'stale',
    last_update: '2026-10-17T08:00:00Z',
    age_hours: 99,
    error_count: 3,
    is_synthetic: false,
    stale_limit_hours: 48,
  },
  {
    source: 'component_prices',
    kind: 'component',
    status: 'missing',
    last_update: null,
    age_hours: null,
    error_count: 0,
    is_synthetic: false,
    stale_limit_hours: 168,
  },
]

const PREDICTED_VS_REALIZED = {
  items: [],
  total: 0,
  summary: {
    total: 0,
    in_range_count: 0,
    in_range_rate: 0,
    below_p10_count: 0,
    above_p90_count: 0,
    used_recommended_count: 0,
    mean_residual: 0,
    mean_absolute_residual: 0,
  },
}

/**
 * The answer for one request.
 *
 * The paths are matched most specific first. A path that contains a unit
 * identifier is not the same request as the list of units, and getting
 * that wrong hands the page a shape it cannot read.
 */
export function fixtureFor(pathname: string): unknown {
  if (pathname === '/health') {
    return {
      status: 'healthy',
      version: '0.1.0',
      environment: 'test',
      checks: { database: 'ok', redis: 'ok' },
    }
  }
  if (pathname.includes('/predicted-vs-realized')) return PREDICTED_VS_REALIZED
  if (pathname.endsWith('/analytics/north-star')) return NORTH_STAR
  if (pathname.endsWith('/analytics/regret-over-time')) return REGRET
  if (pathname.endsWith('/analytics/calibration')) return CALIBRATION
  if (pathname.endsWith('/analytics/override-rate')) return OVERRIDE_RATE
  if (pathname.endsWith('/sources/health')) return SOURCE_HEALTH
  if (pathname.includes('/distribution')) return DISTRIBUTION
  if (pathname.includes('/decisions/')) return DECISION
  if (pathname.endsWith('/decisions')) {
    return {
      items: [
        {
          id: DECISION_ID,
          unit_id: UNIT_ID,
          created_at: '2026-10-20T11:00:00Z',
          recommended_channel: 'RESELL_OPEN_BOX',
          confidence: 0.86,
          fallback_used: false,
          risk_profile: 'balanced',
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    }
  }
  if (pathname.includes('/inspections')) return [INSPECTION]
  if (pathname.endsWith('/skus')) return [SKU]
  if (pathname.includes('/units/')) {
    return { ...UNIT, inspections: [INSPECTION], photos: [] }
  }
  if (pathname.endsWith('/units')) {
    return [
      UNIT,
      {
        ...UNIT,
        id: '66666666-6666-6666-6666-666666666666',
        serial: 'C02SECOND0002',
        status: 'received',
      },
    ]
  }
  return {}
}
