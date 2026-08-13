import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import type { ChartSpec, RunDetail, RunSummary } from '../../shared/types'

const ACTIVE_STATES = ['queued', 'running']

function BarChart({ chart }: { chart: ChartSpec }) {
  const max = Math.max(...chart.values, 1)
  const barWidth = 100 / chart.values.length
  return (
    <svg viewBox="0 0 100 58" role="img" aria-label={chart.alt} className="runchart__svg">
      {chart.values.map((value, index) => (
        <rect
          key={chart.labels[index]}
          x={index * barWidth + barWidth * 0.15}
          y={50 - (value / max) * 46}
          width={barWidth * 0.7}
          height={(value / max) * 46}
          rx="1"
          fill="var(--accent-solid)"
        />
      ))}
      <line x1="0" y1="50" x2="100" y2="50" stroke="var(--border-strong)" strokeWidth="0.5" />
      {chart.labels.map((label, index) => (
        <text
          key={label}
          x={index * barWidth + barWidth / 2}
          y="56"
          textAnchor="middle"
          fontSize="3.4"
          fill="var(--text-faint)"
        >
          {label.length > 9 ? `${label.slice(0, 8)}…` : label}
        </text>
      ))}
    </svg>
  )
}

function LineChart({ chart }: { chart: ChartSpec }) {
  const max = Math.max(...chart.values, 1)
  const min = Math.min(...chart.values, 0)
  const span = max - min || 1
  const points = chart.values
    .map((value, index) => {
      const x = (index / Math.max(chart.values.length - 1, 1)) * 96 + 2
      const y = 48 - ((value - min) / span) * 42
      return `${x},${y}`
    })
    .join(' ')
  return (
    <svg viewBox="0 0 100 58" role="img" aria-label={chart.alt} className="runchart__svg">
      <polyline points={points} fill="none" stroke="var(--accent-solid)" strokeWidth="1.4" />
      <line x1="0" y1="50" x2="100" y2="50" stroke="var(--border-strong)" strokeWidth="0.5" />
      <text x="2" y="56" fontSize="3.4" fill="var(--text-faint)">
        {chart.labels[0]}
      </text>
      <text x="98" y="56" fontSize="3.4" textAnchor="end" fill="var(--text-faint)">
        {chart.labels[chart.labels.length - 1]}
      </text>
    </svg>
  )
}

const TASK_ICON: Record<string, string> = {
  succeeded: '✓',
  failed: '✕',
  skipped: '—',
  cancelled: '—',
  running: '…',
  awaiting_approval: '!',
  pending: '·',
}

/** Arrow-key movement inside the analytics-type tablist. Selection
 *  follows focus, which is the expected behaviour when switching panels
 *  is cheap — here it only swaps already-loaded text. */
function nextTabIndex(key: string, current: number, count: number): number | null {
  if (key === 'ArrowRight') return (current + 1) % count
  if (key === 'ArrowLeft') return (current - 1 + count) % count
  if (key === 'Home') return 0
  if (key === 'End') return count - 1
  return null
}

export function RunsView() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [run, setRun] = useState<RunDetail | null>(null)
  const [goal, setGoal] = useState('Analyze the sample sales dataset and produce a business report')
  const [useUpload, setUseUpload] = useState(false)
  const [csvDraft, setCsvDraft] = useState('')
  const [fileName, setFileName] = useState<string | null>(null)
  // Stepping stops for two different reasons: the user paused the run
  // (durable, server-side, also obeyed by a background worker) or a
  // request failed (local to this tab, cleared on the next action).
  const [stoppedByError, setStoppedByError] = useState(false)
  // Which analytics type's report is on screen. Descriptive is the floor
  // of the maturity ladder, so it opens first.
  const [openReport, setOpenReport] = useState('descriptive')
  const [busy, setBusy] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const advancing = useRef(false)

  const refreshList = useCallback(async () => {
    try {
      const result = await api.listRuns()
      setRuns(result.runs)
    } catch {
      /* list refresh is best-effort; the create/open flows surface errors */
    }
  }, [])

  useEffect(() => {
    void refreshList()
  }, [refreshList])

  // Bounded client-driven stepping: one task per tick while the run is
  // active and auto-run is on. Pausing simply stops advancing — the run
  // state is durable on the server either way.
  useEffect(() => {
    if (!run || run.paused || stoppedByError || !ACTIVE_STATES.includes(run.state)) return
    const throttled = errorMessage?.startsWith('Slowing down') ?? false
    const timer = setTimeout(async () => {
      if (advancing.current) return
      advancing.current = true
      try {
        setRun(await api.advanceRun(run.id))
        setErrorMessage(null)
      } catch (error) {
        if (error instanceof ApiError && error.status === 429) {
          // Throttled: keep the run active and let the next tick retry
          // instead of abandoning a half-finished pipeline.
          setErrorMessage('Slowing down to stay within the request limit…')
        } else {
          setErrorMessage(error instanceof ApiError ? error.message : 'Advance failed.')
          setStoppedByError(true)
        }
      } finally {
        advancing.current = false
      }
    }, throttled ? 1500 : 350)
    return () => clearTimeout(timer)
  }, [run, stoppedByError, errorMessage])

  async function createRun(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setErrorMessage(null)
    try {
      const detail = await api.createRun(
        goal.trim(),
        useUpload && csvDraft.trim() ? csvDraft : undefined,
        useUpload && csvDraft.trim() ? (fileName ?? 'pasted CSV') : undefined,
      )
      setRun(detail)
      setStoppedByError(false)
      void refreshList()
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : 'Could not start the run.')
    } finally {
      setBusy(false)
    }
  }

  async function act(action: () => Promise<RunDetail>) {
    setBusy(true)
    setErrorMessage(null)
    try {
      setRun(await action())
      void refreshList()
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : 'The action failed.')
    } finally {
      setBusy(false)
    }
  }

  function moveTabFocus(event: React.KeyboardEvent, types: string[]) {
    const target = nextTabIndex(event.key, types.indexOf(openReport), types.length)
    if (target === null) return
    event.preventDefault()
    const type = types[target]
    setOpenReport(type)
    document.getElementById(`reporttab-${type}`)?.focus()
  }

  const pendingApproval = run?.approvals.find((a) => a.state === 'pending')

  if (!run) {
    return (
      <section className="panel" aria-label="Runs">
        <div className="panel__inner">
          <div className="panel__header">
            <div>
              <h2 className="panel__title">Analytics runs</h2>
              <p className="panel__desc">
                A goal becomes a governed pipeline of specialist agents — planning, data
                profiling, cleaning, analysis, visualization, validation, and reporting —
                with every claim traced to a calculation and publishing gated by your
                approval.
              </p>
            </div>
          </div>

          <div className="card">
            <form onSubmit={createRun}>
              <div className="field">
                <label className="field__label" htmlFor="run-goal">
                  Goal
                </label>
                <input
                  id="run-goal"
                  className="field__input"
                  value={goal}
                  maxLength={500}
                  onChange={(event) => setGoal(event.target.value)}
                  disabled={busy}
                />
              </div>
              <div className="field">
                <span className="field__label" id="dataset-label">
                  Dataset
                </span>
                <div className="segmented" role="group" aria-labelledby="dataset-label">
                  <button
                    type="button"
                    className="segmented__option"
                    aria-pressed={!useUpload}
                    onClick={() => setUseUpload(false)}
                  >
                    Sample sales data
                  </button>
                  <button
                    type="button"
                    className="segmented__option"
                    aria-pressed={useUpload}
                    onClick={() => setUseUpload(true)}
                  >
                    Upload or paste CSV
                  </button>
                </div>
              </div>
              {useUpload ? (
                <>
                  <div className="field">
                    <label className="field__label" htmlFor="run-file">
                      Choose a CSV file
                    </label>
                    <span className="field__help">
                      Up to 2 MB and 50,000 rows. The file is read in your browser and
                      sent once; identical files are stored only once.
                    </span>
                    <input
                      id="run-file"
                      className="field__input"
                      type="file"
                      accept=".csv,text/csv"
                      disabled={busy}
                      onChange={(event) => {
                        const file = event.target.files?.[0]
                        if (!file) return
                        if (file.size > 2_000_000) {
                          setErrorMessage(
                            `${file.name} is ${(file.size / 1_000_000).toFixed(1)} MB — the limit is 2 MB.`,
                          )
                          return
                        }
                        const reader = new FileReader()
                        reader.onload = () => {
                          setCsvDraft(String(reader.result ?? ''))
                          setFileName(file.name)
                          setErrorMessage(null)
                        }
                        reader.onerror = () => setErrorMessage(`Could not read ${file.name}.`)
                        reader.readAsText(file)
                      }}
                    />
                    {fileName ? (
                      <p className="privacy-note">
                        <Icon name="check" size={14} />
                        {fileName} · {csvDraft.split('\n').filter(Boolean).length - 1} data rows
                      </p>
                    ) : null}
                  </div>
                  <div className="field">
                    <label className="field__label" htmlFor="run-csv">
                      …or paste CSV directly (first row is the header)
                    </label>
                    <textarea
                      id="run-csv"
                      className="field__input runform__textarea"
                      rows={6}
                      value={csvDraft}
                      onChange={(event) => {
                        setCsvDraft(event.target.value)
                        setFileName(null)
                      }}
                      placeholder={'team,quarter,sales\nA,Q1,100\nB,Q1,90'}
                      disabled={busy}
                    />
                  </div>
                </>
              ) : null}
              <div className="field">
                <button type="submit" className="btn btn--primary" disabled={busy || !goal.trim()}>
                  {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="sparkle" size={16} />}
                  Start run
                </button>
              </div>
            </form>
            <p
              className={`statusline ${errorMessage ? 'statusline--error' : ''}`}
              role="status"
              aria-live="polite"
            >
              {errorMessage ?? ''}
            </p>
          </div>

          {runs.length > 0 ? (
            <div className="card">
              <h3 className="card__title">Previous runs</h3>
              <ul className="controls__list">
                {runs.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className="controlrow"
                      onClick={() => void act(() => api.getRun(item.id))}
                    >
                      <Icon name="clock" size={17} />
                      <span>
                        <span className="controlrow__label">{item.goal}</span>
                        <span className="controlrow__help">
                          {item.dataset_name} · {item.state.replace(/_/g, ' ')}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </section>
    )
  }

  return (
    <section className="panel" aria-label="Run detail">
      <div className="panel__inner panel__inner--split">
        <div className="panel__column">
          <div className="panel__header">
            <div>
              <h2 className="panel__title">{run.goal}</h2>
              <p className="panel__desc">
                {run.dataset_name} · state:{' '}
                <strong>{run.state.replace(/_/g, ' ')}</strong>
                {run.error ? ` — ${run.error}` : ''}
              </p>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              {ACTIVE_STATES.includes(run.state) ? (
                <>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    disabled={busy}
                    onClick={() => {
                      setStoppedByError(false)
                      void act(() => (run.paused ? api.resumeRun(run.id) : api.pauseRun(run.id)))
                    }}
                  >
                    {run.paused ? 'Resume' : 'Pause'}
                  </button>
                  <button
                    type="button"
                    className="btn btn--subtle"
                    onClick={() => void act(() => api.cancelRun(run.id))}
                    disabled={busy}
                  >
                    Cancel
                  </button>
                </>
              ) : null}
              <button type="button" className="btn btn--ghost" onClick={() => setRun(null)}>
                All runs
              </button>
            </div>
          </div>

          {pendingApproval ? (
            <div className="card approvalcard" role="region" aria-label="Approval required">
              <h3 className="card__title">
                <Icon name="alert" size={16} /> Approval required
              </h3>
              <dl>
                <div className="rail__row">
                  <dt>Action</dt>
                  <dd style={{ maxWidth: '70%', whiteSpace: 'normal', textAlign: 'right' }}>
                    {pendingApproval.action}
                  </dd>
                </div>
                <div className="rail__row">
                  <dt>Target</dt>
                  <dd style={{ maxWidth: '70%', whiteSpace: 'normal', textAlign: 'right' }}>
                    {pendingApproval.target}
                  </dd>
                </div>
                <div className="rail__row">
                  <dt>Risk</dt>
                  <dd>{pendingApproval.risk}</dd>
                </div>
                <div className="rail__row">
                  <dt>Impact</dt>
                  <dd style={{ maxWidth: '70%', whiteSpace: 'normal', textAlign: 'right' }}>
                    {pendingApproval.impact}
                  </dd>
                </div>
                <div className="rail__row">
                  <dt>Reversibility</dt>
                  <dd style={{ maxWidth: '70%', whiteSpace: 'normal', textAlign: 'right' }}>
                    {pendingApproval.reversibility}
                  </dd>
                </div>
              </dl>
              <div className="dialog__actions">
                <button
                  type="button"
                  className="btn btn--ghost"
                  disabled={busy}
                  onClick={() => void act(() => api.decideApproval(run.id, pendingApproval.id, 'reject'))}
                >
                  Reject
                </button>
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={busy}
                  onClick={() => void act(() => api.decideApproval(run.id, pendingApproval.id, 'approve'))}
                >
                  Approve and publish
                </button>
              </div>
            </div>
          ) : null}

          {run.charts.length > 0 ? (
            <div className="card">
              <h3 className="card__title">Charts</h3>
              {run.charts.map((chart) => (
                <figure key={chart.id} className="runchart">
                  <figcaption className="field__label">{chart.title}</figcaption>
                  {chart.type === 'bar' ? <BarChart chart={chart} /> : <LineChart chart={chart} />}
                </figure>
              ))}
            </div>
          ) : null}

          {run.reports.length ? (
            <div className="card">
              <h3 className="card__title">Reports by analytics type</h3>
              <div
                className="reporttabs"
                role="tablist"
                aria-label="Analytics type"
                onKeyDown={(event) => moveTabFocus(event, run.reports.map((s) => s.type))}
              >
                {run.reports.map((section) => (
                  <button
                    key={section.type}
                    type="button"
                    role="tab"
                    id={`reporttab-${section.type}`}
                    aria-selected={openReport === section.type}
                    aria-controls={`reportpanel-${section.type}`}
                    // Roving tabindex: one stop for the whole tablist, then
                    // the arrow keys move within it (WAI-ARIA tabs pattern).
                    tabIndex={openReport === section.type ? 0 : -1}
                    className={`reporttab ${openReport === section.type ? 'reporttab--on' : ''}`}
                    onClick={() => setOpenReport(section.type)}
                  >
                    <span className="reporttab__name">{section.type}</span>
                    <span className="reporttab__q">{section.question}</span>
                  </button>
                ))}
              </div>
              {run.reports
                .filter((section) => section.type === openReport)
                .map((section) => (
                  <div
                    key={section.type}
                    role="tabpanel"
                    id={`reportpanel-${section.type}`}
                    aria-labelledby={`reporttab-${section.type}`}
                  >
                    {section.headline ? (
                      <p className="reporthead">{section.headline}</p>
                    ) : null}
                    {/* The <pre> is what scrolls, so the tab stop belongs
                        here rather than on the panel around it. */}
                    <pre
                      className="runreport"
                      tabIndex={0}
                      role="region"
                      aria-label={`${section.type} report text`}
                    >
                      {section.content}
                    </pre>
                  </div>
                ))}
            </div>
          ) : null}

          {run.report ? (
            <div className="card">
              <h3 className="card__title">
                Comprehensive report (v{run.report.version})
                {run.report.published_path ? ' — published to the vault' : ''}
              </h3>
              {run.report.published_path ? (
                <p className="privacy-note">
                  <Icon name="check" size={14} /> {run.report.published_path}
                </p>
              ) : null}
              <pre
                className="runreport runreport--full"
                tabIndex={0}
                role="region"
                aria-label="Comprehensive report text"
              >
                {run.report.content}
              </pre>
            </div>
          ) : null}

          <p
            className={`statusline ${errorMessage ? 'statusline--error' : ''}`}
            role="status"
            aria-live="polite"
          >
            {errorMessage ?? ''}
          </p>
        </div>

        <div className="panel__column panel__column--side">
          <div className="card">
            <h3 className="card__title">Specialist pipeline</h3>
            <ul className="runtasks" aria-live="polite">
              {run.tasks.map((task) => (
                <li key={task.id} className={`runtask runtask--${task.state}`}>
                  <span className="runtask__mark" aria-hidden="true">
                    {TASK_ICON[task.state] ?? '·'}
                  </span>
                  <span>
                    <span className="controlrow__label">{task.title}</span>
                    {task.summary ? (
                      <span className="controlrow__help">{task.summary}</span>
                    ) : (
                      <span className="controlrow__help">{task.state.replace(/_/g, ' ')}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
