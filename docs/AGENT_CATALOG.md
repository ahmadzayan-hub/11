# Agent Catalog

The analytics run executes a governed pipeline of specialist agents. Each
is a typed, deterministic stage (`server/analytics.py`) — not a persona in
a chat loop — returning a structured result:

```
status · summary · claims[] · calculations[] · quality_checks[] · output
```

Claims carry `evidence` (calculation ids) and a `status`; the Validation
Expert independently re-verifies them. Pattern selection is recorded by
the Planner (sequential governed pipeline — the simplest sufficient
pattern for a repeatable analytics workflow, with a fixed bounded stage
list as the stopping rule).

| # | Agent | Responsibility | Can fail the run |
| --- | --- | --- | --- |
| 1 | Orchestrator (run engine) | State machine, budgets, approval gate, recovery | — |
| 2 | Planner Agent | Records the plan, pattern choice, and stopping rule | no |
| 3 | Data Source Agent | CSV ingestion, size/row limits, snapshot hash | yes |
| 4 | Data Profiling Agent | Completeness, duplicates, types, numeric detection | yes (no numeric data) |
| 5 | Data Cleaning Agent | Trim, dedupe, coercion — row loss always reported | yes |
| 6 | Data Preparation Agent | Measure/dimension selection, aggregates, trend | yes |
| 7 | Exploratory Data Analyst | Descriptive stats, growth, top-group share, outliers | yes |
| 8 | Visualization Expert | Truthful chart specs (zero-based axes, alt text) | no |
| 9 | Business Analyst Agent | Insights labelled finding vs recommendation; narrative via model gateway (source labelled) | no |
| 10 | Validation Expert | Reconciles totals, row accounting, claim-evidence coverage; may reject, never rewrites | rejects → partially_completed |
| 11 | Reporting Expert | Markdown report with claims-evidence matrix and limitations | no |
| 12 | Knowledge Curator (publish) | Approval-gated write-back to the Obsidian vault with provenance frontmatter | approval required |

## Independence rules implemented

- The Validation Expert receives artifacts and acceptance criteria, not
  hidden reasoning, and re-computes checks deterministically.
- Publishing (the only side-effecting stage) is server-enforced behind an
  approval bound to the exact artifact hash.
- The model narrator never contributes numbers; its text is labelled with
  its source (`model` or `deterministic`) in the report.

## Not implemented (honest scope)

Statistical-testing, forecasting, optimization, governance/PII,
red-team, and cost agents from the V2 catalog are not implemented — they
require capabilities (inference libraries, LLM evaluation, PII models)
that would be placeholders today. The pipeline’s typed stage contract is
the extension point for them.
