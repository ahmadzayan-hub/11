import { expect, test } from '@playwright/test'
import { openTab, skipOnboarding } from './helpers'

test('analytics run: goal to approved, published, evidence-backed report', async ({ page }) => {
  await skipOnboarding(page)
  await page.goto('/')
  await openTab(page, /^Runs/)

  await expect(page.getByLabel('Goal')).toHaveValue(/sample sales dataset/)
  await page.getByRole('button', { name: 'Start run' }).click()

  // The pipeline advances stage by stage until the approval gate.
  const approval = page.getByRole('region', { name: 'Approval required' })
  await expect(approval).toBeVisible({ timeout: 20_000 })
  await expect(approval).toContainText('high')
  await expect(page.getByText('state: awaiting approval')).toBeVisible()

  // All ten specialists succeeded and the evidence is visible.
  await expect(page.locator('.runtask--succeeded')).toHaveCount(10)
  await expect(
    page.locator('.runtasks').getByText('All validation checks passed', { exact: false }),
  ).toBeVisible()
  await expect(page.locator('.runchart__svg')).toHaveCount(2)
  await expect(page.locator('.runreport')).toContainText('Findings and claims')
  await expect(page.locator('.runreport')).toContainText('verified')

  // Approve: the report is published to the Obsidian-compatible vault.
  await approval.getByRole('button', { name: 'Approve and publish' }).click()
  await expect(page.getByText('published to the vault', { exact: false })).toBeVisible()
  await expect(page.getByText('state: completed')).toBeVisible()
})

test('analytics run can be cancelled', async ({ page }) => {
  await skipOnboarding(page)
  await page.goto('/')
  await openTab(page, /^Runs/)
  await page.getByRole('button', { name: 'Start run' }).click()
  await page.getByRole('button', { name: 'Cancel', exact: true }).click()
  await expect(page.getByText('state: cancelled')).toBeVisible()
})
