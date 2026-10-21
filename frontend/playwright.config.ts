import { defineConfig, devices } from '@playwright/test'

/**
 * The visual regression configuration.
 *
 * The suite runs against the built application rather than the development
 * server, because what is tested should be what is shipped. The API is
 * answered with fixtures, so the suite needs no backend and never depends
 * on what happens to be in the database.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['github'], ['list']] : [['list']],
  timeout: 30000,
  expect: {
    // The fonts are rendered by the browser, so a line of text can land a
    // pixel either side of where it did last time.
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
      animations: 'disabled',
    },
  },
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    // The same viewport in both themes, so the two sets of screenshots can
    // be compared with each other.
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
  },
  projects: [
    {
      name: 'dark',
      use: {
        ...devices['Desktop Chrome'],
        colorScheme: 'dark',
      },
    },
    {
      name: 'light',
      use: {
        ...devices['Desktop Chrome'],
        colorScheme: 'light',
      },
    },
  ],
  webServer: {
    command: 'npm run build && npm run preview -- --port 4173 --host 127.0.0.1',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
