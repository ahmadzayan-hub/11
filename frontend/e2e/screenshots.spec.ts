import { test } from '@playwright/test'
import { lastAgentBubble, sendMessage, skipOnboarding } from './helpers'

// Captures the final interface for the documentation. Runs last in file
// order but is independent of the other specs.
test('capture interface screenshots', async ({ page }, testInfo) => {
  await skipOnboarding(page)
  await page.goto('/')
  await sendMessage(page, 'Hello! What can you do?')
  await lastAgentBubble(page).waitFor()
  await sendMessage(page, '/help')
  await lastAgentBubble(page).waitFor()

  await page.screenshot({
    path: `../docs/screenshots/${testInfo.project.name}-chat-light.png`,
    fullPage: false,
  })

  await page.getByRole('button', { name: 'Switch to dark theme' }).click()
  await page.screenshot({
    path: `../docs/screenshots/${testInfo.project.name}-chat-dark.png`,
    fullPage: false,
  })
})
