import { expect, test, type Page } from '@playwright/test'
import { fixtureFor } from './fixtures'

/**
 * The visual suite for the storefront.
 *
 * The suite is hermetic. The API is answered with fixtures and the
 * photographs with a picture, so the screenshots are the same whatever
 * is in the database.
 */

/** A picture, so that a photograph is a photograph and not a broken image. */
const PHOTOGRAPH = Buffer.from(
  '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q==',
  'base64',
)

/**
 * Answer the API with the fixtures.
 *
 * @param page - The page.
 */
async function stubApi(page: Page) {
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(fixtureFor(url.pathname)),
    })
  })

  await page.route('**/uploads/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'image/jpeg', body: PHOTOGRAPH })
  })
}

test.describe('the shop window', () => {
  test.beforeEach(async ({ page }) => {
    await stubApi(page)
  })

  test('the window shows the devices', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Refurbished, inspected, priced.' })).toBeVisible()
    await expect(page.getByText('M3 Pro 2023 512')).toBeVisible()
    await expect(page.getByText('$1,499.50')).toBeVisible()
    await expect(page).toHaveScreenshot('window.png', { fullPage: true })
  })

  test('the window says the prices are modelled', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('These prices are modelled')).toBeVisible()
  })

  test('a device has its own page', async ({ page }) => {
    await page.goto('/device/ecf6f4b8-0a7b-4185-b0f1-8b77ba5a4318')
    await expect(page.getByRole('heading', { name: 'M3 Pro 2023 512' })).toBeVisible()
    await expect(page.getByText('What was tested')).toBeVisible()
    await expect(page.getByText('In the box')).toBeVisible()
    await expect(page).toHaveScreenshot('device.png', { fullPage: true })
  })

  test('a device can be reached from the window', async ({ page }) => {
    await page.goto('/')
    await page.getByText('M3 Pro 2023 512').click()
    await expect(page).toHaveURL(/\/device\//)
  })

  test('the window is navigable by keyboard', async ({ page }) => {
    await page.goto('/')
    const device = page.getByRole('link', { name: /M3 Pro 2023 512/ })

    // The device is reachable without a mouse: the tab order runs from
    // the header through the filter to the cards.
    let found = false
    for (let press = 0; press < 20 && !found; press += 1) {
      await page.keyboard.press('Tab')
      found = await device.evaluate((node) => node === document.activeElement)
    }
    expect(found).toBe(true)

    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/device\//)
  })
})
