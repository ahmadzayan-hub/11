import { test } from '@playwright/test'
import { lastAgentBubble, openTab, sendMessage, skipOnboarding } from './helpers'

// Captures the final interface for the documentation. Runs last in file
// order but is independent of the other specs. Themes are stamped
// directly because the header toggle is hidden on narrow viewports.
test('capture interface screenshots', async ({ page }, testInfo) => {
  await skipOnboarding(page)
  await page.goto('/')
  const shot = (name: string) =>
    page.screenshot({ path: `../docs/screenshots/${testInfo.project.name}-${name}.png` })
  const theme = (value: string) =>
    page.evaluate((themeValue) => {
      document.documentElement.dataset.theme = themeValue
    }, value)

  await theme('dark')
  await page.getByText('What would you like to accomplish?').waitFor()
  await shot('hero-dark')

  await sendMessage(page, 'Hello! What can you do?')
  await lastAgentBubble(page).waitFor()
  await sendMessage(page, '/help')
  await lastAgentBubble(page).waitFor()

  await theme('light')
  await shot('chat-light')
  await theme('dark')
  await shot('chat-dark')

  if (testInfo.project.name === 'desktop') {
    await openTab(page, /^Memory/)
    await page.getByText('Data controls').waitFor()
    await shot('memory-dark')

    await openTab(page, /^Activity/)
    await page.getByText('Session health').waitFor()
    await shot('activity-dark')

    await openTab(page, /^Runs/)
    await page.getByRole('button', { name: 'Start run' }).click()
    await page
      .getByRole('region', { name: 'Approval required' })
      .waitFor({ timeout: 20_000 })
    await shot('runs-dark')
  }
})
