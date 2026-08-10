import { expect, test } from '@playwright/test'
import { composerInput, lastAgentBubble, sendMessage, skipOnboarding } from './helpers'

test('session survives a page refresh', async ({ page }) => {
  await skipOnboarding(page)
  await page.goto('/')
  await expect(composerInput(page)).toBeVisible()

  await sendMessage(page, 'Keep this conversation across refreshes')
  await expect(lastAgentBubble(page)).toBeVisible()

  await page.reload()

  // The same transcript is restored instead of a fresh empty session.
  await expect(
    page.locator('.msg--user .msg__bubble', {
      hasText: 'Keep this conversation across refreshes',
    }),
  ).toBeVisible()
  await expect(page.getByRole('status').filter({ hasText: 'Ready' })).toBeVisible()
  await expect(composerInput(page)).toBeEnabled()
})

test('offline mode clears after a confirmed successful request', async ({ page }) => {
  await skipOnboarding(page)
  await page.goto('/')
  await expect(composerInput(page)).toBeVisible()

  // Simulate a dead backend: the send fails and the app reports offline.
  await page.route('**/api/**', (route) => route.abort())
  await sendMessage(page, 'This one fails')
  await expect(page.getByRole('status').filter({ hasText: 'Offline' })).toBeVisible()

  // Backend recovers WITHOUT a browser online event. A successful retry
  // must clear the offline badge (regression: it used to stay stuck).
  await page.unroute('**/api/**')
  await page.getByRole('button', { name: 'Retry' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Ready' })).toBeVisible()
  await expect(page.locator('.msg--agent .msg__bubble').last()).toContainText('This one fails')
})
