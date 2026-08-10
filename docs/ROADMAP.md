# Release Roadmap and Scope Control

The greatest project risk is uncontrolled scope, not a missing agent.
This roadmap fixes three release tiers with measurable gates, based on an
independent architecture review of the V2 specification. Nothing in a
later tier may be presented as shipped before its gate passes.

## Tier 1 — Academic MVP (SHIPPED, evidence in docs/UI_UX_AUDIT.md)

Deterministic assistant (CLI + web), durable analytics run engine with a
governed ten-specialist pipeline, claim–evidence validation, approval-
gated Obsidian vault publishing, provider-neutral model gateway
(deterministic default, optional Groq narration), mobile-first PWA,
security hardening, CI gates. Evidence: 88 Python + 18 unit + 23 e2e
tests green in CI; Lighthouse 95/100/100/100; clean npm audit.

Standing rule already enforced and carried forward: **raw datasets are
never sent to a model provider** — only deterministic, already-verified
facts reach the narrator.

## Tier 2 — Production MVP (next; each item needs an ADR + release gate)

1. Managed authentication (OIDC adapter) with Owner/Admin/Analyst/Viewer
   roles; fail-closed in production mode.
2. PostgreSQL adapter behind the existing `RunEngine`/memory interfaces,
   plus object storage for datasets and artifacts; migration tooling,
   backups, and restore drills (documented RPO/RTO).
   **Done:** run-engine Postgres adapter shipped and CI-enforced against
   Postgres 16; Supabase project `agentic-os` provisioned, RLS
   deny-by-default; sessions, memory, and published vault notes all moved
   behind the store, so the backend requires no local disk (ADR 0001 and
   its amendment). **Remaining:** object storage for large datasets;
   backups and restore drills (RPO/RTO).
3. Durable workflow execution: evaluate **Vercel Workflows for Python**
   directly against the run-engine contract (pause/resume/recovery)
   before committing to the abstraction; otherwise database-backed jobs
   with leases and heartbeats.
4. Scalable analytics data plane: DuckDB or Polars for bounded local
   analysis, resumable uploads, dataset size/memory limits, partitioning
   and sampling, restricted-data egress controls.
5. Verified Vercel deployment (frontend) against the hosted API; preview
   deployments per PR; rollback documented.
6. Tenant quotas, usage budgets, and cost tracking (FinOps foundation).

## Tier 3 — Enterprise Release (scoped, not started)

- **Metric governance:** business glossary, certified KPI workflow with
  ownership, fiscal calendars, slowly changing dimensions, schema
  evolution and impact analysis, row/column-level security, entity
  resolution.
- **Experimentation and causal inference:** power analysis, A/B and
  sequential testing, multiple-testing control, sample-ratio-mismatch
  detection, explicit confounding and counterfactual limitations.
- **UAE PDPL compliance:** data-residency decisions, cross-border
  transfer controls, processor registers, consent evidence, privacy
  impact assessments, deletion across primary storage, embeddings,
  telemetry, and backups.
- **Business continuity:** SLOs and error budgets, point-in-time
  recovery, incident classification and on-call ownership, load/soak/
  failover/chaos testing, provider-exit procedures.
- **Supply chain:** SBOM, signed artifacts, build provenance, license
  scanning, pinned actions/packages, vendor registers and contingency.
- **Android release lifecycle:** Capacitor project, Play App Signing,
  developer verification (regional from 2026-09-30), testing tracks,
  Data Safety declaration, Play Integrity, crash/ANR monitoring,
  real-device matrix. (The PWA remains the supported mobile path until
  this gate passes.)
- **Collaboration and accountability:** comments, mentions, delegated
  approvals, artifact permissions, notifications, and an explicit RACI.
- **Obsidian privacy lifecycle:** local-only mode, zero-server-copy
  option, key ownership, embedding/backup deletion, sync diagnostics,
  plugin release review.

## Additional governed capabilities (only four — no decorative agents)

1. Data Platform and Data Contract Agent
2. Experiment and Causal Inference Agent
3. Pluggable Domain Expert Agent
4. Reliability and Incident Management Agent

Each enters the catalog only with the full typed contract
(entry/exit criteria, budgets, quality checks, evaluation suite) defined
in `docs/AGENT_CATALOG.md`.

## Decision records

Key decisions to date are recorded in `docs/ARCHITECTURE.md`. From Tier 2
onward, every choice listed above (database, object storage, workflow
engine, identity provider, analytics engine, Obsidian sync, Android
approach) requires a versioned ADR under `docs/adr/`.
