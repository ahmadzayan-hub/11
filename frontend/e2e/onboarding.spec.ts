import { expect, test } from '@playwright/test'
import { composerInput } from './helpers'

test('first visit shows dismissible onboarding that never returns', async ({ page }) => {
  await page.goto('/')

  const dialog = page.getByRole('dialog', { name: 'Welcome to Agentic OS' })
  await expect(dialog).toBeVisible()
  await expect(dialog).toContainText('Memory is stored locally')

  await dialog.getByRole('button', { name: 'Get started' }).click()
  await expect(dialog).toBeHidden()

  await page.reload()
  await expect(composerInput(page)).toBeVisible()
  await expect(page.getByRole('dialog', { name: 'Welcome to Agentic OS' })).toBeHidden()
})
