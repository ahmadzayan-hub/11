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
