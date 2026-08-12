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
| 7 | **Descriptive Analytics Agent** — *what happened?* | Totals, typical values, spread, period change, largest segment, unusual records | yes (no usable values) |
| 8 | **Diagnostic Analytics Agent** — *why did it happen?* | Decomposes the change by segment (parts must sum to the whole) and measures which columns move together — association, never cause | no |
| 9 | **Predictive Analytics Agent** — *what will happen?* | Trend fitted to history and extended, with accuracy measured by backtesting against held-out periods; declines to forecast below 4 periods | no |
| 10 | **Prescriptive Analytics Agent** — *what should I do?* | Enumerates options the data supplies, scores each under one stated assumption, recommends one and says what would change the answer | no |
| 11 | Visualization Expert | Truthful chart specs (zero-based axes, alt text): totals by segment, trend, who-moved-it, history-and-forecast | no |
| 12 | Validation Expert | Reconciles totals and the change decomposition, row accounting, claim-evidence coverage, forecast accuracy declared, recommendations carry assumptions, claims free of statistical jargon; may reject, never rewrites | rejects → partially_completed |
| 13 | Reporting Expert | One report per analytics type plus a comprehensive report embedding all four, with the claims-evidence matrix and limitations | no |
| 14 | Knowledge Curator (publish) | Approval-gated write-back to the Obsidian vault with provenance frontmatter | approval required |

## The four types form a ladder

Each level consumes the one below it, which is why they run in this order
and why the pipeline is sequential rather than parallel:

```
Descriptive → Diagnostic → Predictive → Prescriptive
(what?)       (why?)       (what next?)  (what to do?)
```

The prescriptive agent's options come from the diagnostic decomposition
and the predictive forecast; a recommendation with nothing underneath it
would be an opinion.

## Business language is a contract, not a style

Every type answers its question in one plain sentence — the headline —
which is the stage's summary, the top of its report, and the row in the
comprehensive report's summary table. "Costs are rising", not "the mean
increased by 2.3 standard deviations". This is enforced, not encouraged:
`claims_avoid_statistical_jargon` fails validation if a claim or headline
contains statistical vocabulary, and the narrator's system prompt carries
the same rule. Method strings keep their technical precision, because
that is what makes a figure auditable — the distinction is between what
the reader is told and what the reader can check.

## Independence rules implemented

- The Validation Expert receives artifacts and acceptance criteria, not
  hidden reasoning, and re-computes checks deterministically.
- Publishing (the only side-effecting stage) is server-enforced behind an
  approval bound to the exact artifact hash.
- The model narrator never contributes numbers; its text is labelled with
  its source (`model` or `deterministic`) in the report.

## Not implemented (honest scope)

Statistical hypothesis testing, causal inference, seasonality models,
true optimization, governance/PII, red-team, and cost agents are not
implemented — they require capabilities (inference libraries, LLM
evaluation, PII models) that would be placeholders today.

The forecasting and recommendation now shipped are deliberately modest and
say so in their own reports: a straight-line trend with backtested error,
and an option ranking under one stated assumption. Calling either of them
"machine learning" or "optimization" would be a marketing claim, not a
description. The pipeline's typed stage contract is the extension point
when the real thing is warranted.
