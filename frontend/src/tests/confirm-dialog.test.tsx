import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ConfirmDialog } from '../shared/components/ConfirmDialog'

function renderDialog(onConfirm = vi.fn(), onCancel = vi.fn()) {
  render(
    <ConfirmDialog
      title="Clear all memory?"
      message="This cannot be undone."
      confirmLabel="Clear all memory"
      onConfirm={onConfirm}
      onCancel={onCancel}
    />,
  )
  return { onConfirm, onCancel }
}

describe('ConfirmDialog', () => {
  it('moves focus into the dialog when it opens', () => {
    renderDialog()
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
  })

  it('closes on Escape without confirming', async () => {
    const user = userEvent.setup()
    const { onConfirm, onCancel } = renderDialog()

    await user.keyboard('{Escape}')

    expect(onCancel).toHaveBeenCalledOnce()
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('keeps Tab focus trapped inside the dialog', async () => {
    const user = userEvent.setup()
    renderDialog()

    await user.tab()
    expect(screen.getByRole('button', { name: 'Clear all memory' })).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
  })

  it('fires the destructive action only on explicit confirmation', async () => {
    const user = userEvent.setup()
    const { onConfirm } = renderDialog()

    await user.click(screen.getByRole('button', { name: 'Clear all memory' }))

    expect(onConfirm).toHaveBeenCalledOnce()
    expect(screen.getByRole('dialog')).toHaveAccessibleName('Clear all memory?')
  })
})
