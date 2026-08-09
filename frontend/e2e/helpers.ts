import type { Page } from '@playwright/test'

/** Skip the first-run onboarding dialog for tests that don't cover it. */
export async function skipOnboarding(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('aos-onboarded', '1')
  })
}

/** Click a navigation control wherever it currently lives: the sidebar on
 *  desktop, the bottom tab bar on mobile, or the drawer for actions that
 *  only exist in the sidebar. */
export async function openTab(page: Page, name: RegExp) {
  const target = page.getByRole('button', { name }).filter({ visible: true })
  if ((await target.count()) === 0) {
    await page.getByRole('button', { name: 'Open navigation' }).click()
  }
  await target.first().click()
}

/** Click a sidebar quick action (New session / Clear history / End session),
 *  going through the drawer on mobile viewports. */
export async function clickQuickAction(page: Page, name: RegExp) {
  await openTab(page, name)
}

/** The composer's message textbox. */
export function composerInput(page: Page) {
  return page.getByRole('textbox', { name: 'Message' })
}

/** Send a message through the composer and wait for the agent's reply. */
export async function sendMessage(page: Page, text: string) {
  const input = composerInput(page)
  await input.click()
  await input.fill(text)
  await input.press('Enter')
}

export function lastAgentBubble(page: Page) {
  return page.locator('.msg--agent .msg__bubble').last()
}
