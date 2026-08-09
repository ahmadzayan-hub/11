import { Dialog } from '../../shared/components/Dialog'
import type { CommandInfo } from '../../shared/types'

interface HelpDialogProps {
  commands: CommandInfo[]
  onClose: () => void
}

export function HelpDialog({ commands, onClose }: HelpDialogProps) {
  return (
    <Dialog title="Commands" onClose={onClose} wide labelledById="help-title">
      <p className="dialog__body">
        Type these in the composer, pick them from the command palette (<kbd>Ctrl</kbd>+
        <kbd>K</kbd>), or use the quick actions in the sidebar.
      </p>
      <table className="cmdtable">
        <thead>
          <tr>
            <th scope="col">Command</th>
            <th scope="col">What it does</th>
          </tr>
        </thead>
        <tbody>
          {commands.map((command) => (
            <tr key={command.command}>
              <td>
                <code>{command.usage}</code>
              </td>
              <td>{command.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="dialog__actions">
        <button type="button" className="btn btn--ghost" onClick={onClose}>
          Close
        </button>
      </div>
    </Dialog>
  )
}
