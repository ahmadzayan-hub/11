import { expect, test } from '@playwright/test'
import { composerInput, lastAgentBubble, sendMessage, skipOnboarding } from './helpers'

// The journey specs already cover 375 px and 1440 px; this checks the
// remaining required breakpoints.
const WIDTHS = [
  { width: 320, height: 640 },
  { width: 768, height: 1024 },
  { width: 1024, height: 768 },
]

test('no horizontal overflow at 320, 768, and 1024 px', async ({ page }) => {
  test.skip(test.info().project.name !== 'desktop', 'viewport-resize test runs once')
  await skipOnboarding(page)
  await page.goto('/')
  await sendMessage(
    page,
    'A long message with an unbreakable token Supercalifragilisticexpialidocious1234567890 to prove wrapping works.',
  )
  await expect(lastAgentBubble(page)).toBeVisible()

  for (const viewport of WIDTHS) {
    await page.setViewportSize(viewport)
    await expect(composerInput(page)).toBeVisible()
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    expect(overflow, `overflow at ${viewport.width}px`).toBeLessThanOrEqual(0)
  }
})
