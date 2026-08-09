import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CommandPalette } from '../features/commands/CommandPalette'
import type { CommandInfo } from '../shared/types'

const COMMANDS: CommandInfo[] = [
  { command: '/help', usage: '/help', description: 'Show available commands' },
  { command: '/remember', usage: '/remember <information>', description: 'Save information to memory' },
  { command: '/clear', usage: '/clear', description: 'Clear conversation history' },
]

describe('CommandPalette', () => {
  it('lists every command and focuses the search input', () => {
    render(<CommandPalette commands={COMMANDS} onPick={vi.fn()} onClose={vi.fn()} />)
    expect(screen.getByRole('combobox')).toHaveFocus()
    expect(screen.getAllByRole('option')).toHaveLength(3)
  })

  it('filters commands by name and description', async () => {
    const user = userEvent.setup()
    render(<CommandPalette commands={COMMANDS} onPick={vi.fn()} onClose={vi.fn()} />)

    await user.keyboard('memory')

    const options = screen.getAllByRole('option')
    expect(options).toHaveLength(1)
    expect(options[0]).toHaveTextContent('/remember')
  })

  it('shows an empty message when nothing matches', async () => {
    const user = userEvent.setup()
    render(<CommandPalette commands={COMMANDS} onPick={vi.fn()} onClose={vi.fn()} />)

    await user.keyboard('zzz')

    expect(screen.queryAllByRole('option')).toHaveLength(0)
    expect(screen.getByText(/No commands match/)).toBeInTheDocument()
  })

  it('picks the highlighted command with arrow keys and Enter', async () => {
    const onPick = vi.fn()
    const user = userEvent.setup()
    render(<CommandPalette commands={COMMANDS} onPick={onPick} onClose={vi.fn()} />)

    await user.keyboard('{ArrowDown}{Enter}')

    expect(onPick).toHaveBeenCalledExactlyOnceWith(COMMANDS[1])
  })

  it('closes on Escape', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(<CommandPalette commands={COMMANDS} onPick={vi.fn()} onClose={onClose} />)

    await user.keyboard('{Escape}')

    expect(onClose).toHaveBeenCalledOnce()
  })
})
