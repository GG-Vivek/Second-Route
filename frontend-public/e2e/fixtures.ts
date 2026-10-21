/**
 * The fixtures for the storefront's visual suite.
 *
 * The suite is hermetic: the API is answered with these, so the
 * screenshots do not depend on what happens to be in the database.
 */

/** One device. */
export const LISTING = {
  id: 'ecf6f4b8-0a7b-4185-b0f1-8b77ba5a4318',
  title: 'M3 Pro 2023 512',
  family: 'MacBook Pro',
  model_name: 'M3 Pro',
  year: '2023',
  storage_gb: '512',
  ram_gb: '18',
  color: 'Space Gray',
  grade: 'A',
  condition: 'Like new',
  battery_health_pct: '95',
  price: {
    amount: 1499.5,
    currency: 'USD',
    source: 'synthetic',
    as_of: '2026-01-01T09:00:00',
    is_estimate: true,
  },
  photo: { url: '/uploads/fixture-one.jpg', alt: 'M3 Pro, 2023' },
  photo_count: 3,
  listed_at: '2026-01-01T09:00:00',
  in_stock: true,
}

/** A second device, so the window is a grid and not a single card. */
export const SECOND_LISTING = {
  ...LISTING,
  id: '9d2c1f60-0f2e-4a5e-9b1a-2c8f7b6e5d41',
  title: 'M3 Max 2023 1TB',
  family: 'MacBook Pro',
  model_name: 'M3 Max',
  storage_gb: '1TB',
  ram_gb: '36',
  color: 'Silver',
  grade: 'B',
  condition: 'Good',
  battery_health_pct: '88',
  price: { ...LISTING.price, amount: 1899.0 },
  photo: { url: '/uploads/fixture-two.jpg', alt: 'M3 Max, 2023' },
}

/** A third, from another family. */
export const THIRD_LISTING = {
  ...LISTING,
  id: '5a1b2c3d-4e5f-4a6b-8c9d-0e1f2a3b4c5d',
  title: 'X1 Carbon 2024 1TB',
  family: 'ThinkPad X1 Carbon',
  model_name: 'X1 Carbon',
  year: '2024',
  storage_gb: '1TB',
  ram_gb: '32',
  color: 'Black',
  grade: 'B',
  condition: 'Good',
  price: { ...LISTING.price, amount: 1249.25 },
  photo: { url: '/uploads/fixture-three.jpg', alt: 'X1 Carbon, 2024' },
}

/** The page of devices. */
export const LISTING_PAGE = {
  items: [LISTING, SECOND_LISTING, THIRD_LISTING],
  total: 3,
  limit: 24,
  offset: 0,
  families: ['MacBook Pro', 'ThinkPad X1 Carbon'],
  synthetic: true,
}

/** One device, in full. */
export const LISTING_DETAIL = {
  ...LISTING,
  photos: [
    { url: '/uploads/fixture-one.jpg', alt: 'M3 Pro, 2023' },
    { url: '/uploads/fixture-two.jpg', alt: 'M3 Pro, 2023, photograph 2' },
    { url: '/uploads/fixture-three.jpg', alt: 'M3 Pro, 2023, photograph 3' },
  ],
  accessories: ['charger', 'cable'],
  checks: [
    { name: 'display', passed: true },
    { name: 'keyboard', passed: true },
    { name: 'battery', passed: false },
    { name: 'boot', passed: true },
  ],
  highlights: [
    '18 GB memory',
    '512 storage',
    '2023 model',
    'Battery at 95% health',
    'Barely marked. It looks like it was not used.',
  ],
}

/**
 * The answer for a path.
 *
 * @param pathname - The path that was asked for.
 * @returns The body to answer with.
 */
export function fixtureFor(pathname: string): unknown {
  if (pathname.startsWith('/api/v1/public/listings/')) {
    return LISTING_DETAIL
  }
  if (pathname === '/api/v1/public/listings') {
    return LISTING_PAGE
  }
  return {}
}
