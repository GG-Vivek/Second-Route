import { expect, test, type Page } from '@playwright/test'
import { fixtureFor } from './fixtures'

/**
 * Answer every API call with a fixture.
 *
 * The suite is hermetic. A screenshot that depends on what is in the
 * database is a screenshot that fails on somebody else's machine.
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
  await page.route('**/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(fixtureFor('/health')),
    })
  })
}

/**
 * Put the theme in place before the page loads.
 *
 * The theme is a stored choice, not the colour scheme of the operating
 * system, so the project name has to be turned into one. Without this
 * both projects would photograph the same page.
 *
 * The choice is seeded once per tab and not on every load, so that a test
 * can change the theme and reload to see whether the change was kept.
 */
test.beforeEach(async ({ page }, testInfo) => {
  const theme = testInfo.project.name === 'light' ? 'light' : 'dark'
  await page.addInitScript((value) => {
    if (window.sessionStorage.getItem('theme-seeded')) return
    window.sessionStorage.setItem('theme-seeded', 'yes')
    window.localStorage.setItem('secondroute-theme', value)
  }, theme)
})

/** Wait for the page to settle: no spinner left, no layout still moving. */
async function settle(page: Page) {
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(400)
}

const ROUTES: [string, string][] = [
  ['dashboard', '/'],
  ['units', '/units'],
  ['intake', '/intake/new'],
  ['analytics', '/analytics'],
  ['backtest', '/backtest'],
  ['health', '/health'],
]

test.describe('the critical routes', () => {
  for (const [name, path] of ROUTES) {
    test(`${name} looks the way it should`, async ({ page }) => {
      await stubApi(page)
      await page.goto(path)
      await settle(page)

      await expect(page).toHaveScreenshot(`${name}.png`, { fullPage: true })
    })
  }
})

test.describe('the decision card', () => {
  test('shows the landscape', async ({ page }) => {
    await stubApi(page)
    await page.goto('/units/11111111-1111-1111-1111-111111111111/decision')
    await settle(page)

    // The flat view is the one that is always available, and the one
    // that can be compared pixel for pixel.
    await page.getByTestId('landscape-flat').click()
    await page.waitForTimeout(400)

    await expect(page.getByTestId('channel-landscape-2d')).toBeVisible()
    await expect(page).toHaveScreenshot('decision-flat.png', { fullPage: true })
  })

  test('draws the landscape in three dimensions when it can', async ({ page }) => {
    await stubApi(page)
    await page.goto('/units/11111111-1111-1111-1111-111111111111/decision')
    await settle(page)

    const spatial = page.getByTestId('landscape-spatial')
    if (await spatial.isDisabled()) {
      // The browser cannot draw in three dimensions, so the flat view is
      // what it shows. That is the point of the fallback.
      await expect(page.getByTestId('channel-landscape-2d')).toBeVisible()
      return
    }

    await spatial.click()
    await page.waitForTimeout(1200)
    await expect(page.getByTestId('channel-landscape-3d')).toBeVisible()
    await expect(page.getByTestId('channel-landscape-canvas')).toBeAttached()
  })
})

test.describe('the keyboard', () => {
  test('the command palette opens and navigates', async ({ page }) => {
    await stubApi(page)
    await page.goto('/')
    await settle(page)

    await page.keyboard.press('Meta+k')
    const dialog = page.getByRole('dialog', { name: /search the application/i })
    await expect(dialog).toBeVisible()

    await page.keyboard.type('units')
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/units$/)
  })

  test('the escape key closes the palette', async ({ page }) => {
    await stubApi(page)
    await page.goto('/')
    await settle(page)

    await page.keyboard.press('Meta+k')
    await expect(page.getByRole('dialog', { name: /search the application/i })).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog', { name: /search the application/i })).toBeHidden()
  })

  test('the page can be reached with the tab key alone', async ({ page }) => {
    await stubApi(page)
    await page.goto('/')
    await settle(page)

    const seen: string[] = []
    for (let index = 0; index < 25; index++) {
      await page.keyboard.press('Tab')
      const label = await page.evaluate(() => {
        const active = document.activeElement
        if (!active || active === document.body) return ''
        return (
          active.getAttribute('aria-label') ??
          active.textContent?.trim().slice(0, 40) ??
          ''
        )
      })
      if (label) seen.push(label)
    }

    // The navigation and the search have to be reachable without a mouse.
    expect(seen.some((label) => /dashboard|units|search/i.test(label))).toBe(true)
  })
})

test.describe('the theme', () => {
  test('the choice is remembered across a reload', async ({ page }) => {
    await stubApi(page)
    await page.goto('/')
    await settle(page)

    await page.getByTestId('theme-toggle').click()
    const afterFirst = await page.evaluate(() =>
      document.documentElement.classList.contains('dark')
    )

    await page.reload()
    await settle(page)

    const afterReload = await page.evaluate(() =>
      document.documentElement.classList.contains('dark')
    )
    expect(afterReload).toBe(afterFirst)
  })

  test('the two themes really are different', async ({ page }, testInfo) => {
    await stubApi(page)
    await page.goto('/')
    await settle(page)

    const isDark = await page.evaluate(() =>
      document.documentElement.classList.contains('dark')
    )
    expect(isDark).toBe(testInfo.project.name === 'dark')
  })
})
