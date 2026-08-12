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
security hardening, CI gates. Evidence at the time of that gate: 88
Python + 18 unit + 23 e2e tests green in CI; Lighthouse 95/100/100/100;
clean npm audit. (Tier 2 work has since grown the suite to 156 Python +
23 unit + 36 e2e checks.)

Standing rule already enforced and carried forward: **raw datasets are
never sent to a model provider** — only deterministic, already-verified
facts reach the narrator.

## Tier 2 — Production MVP (next; each item needs an ADR + release gate)

1. Managed authentication (OIDC adapter) with Owner/Admin/Analyst/Viewer
   roles; fail-closed in production mode.
   **Done:** identity adapter with local and JWT (shared-secret or JWKS)
   providers, server-side role permissions on every endpoint, per-owner
   isolation for sessions and runs, fail-closed production startup, an
   attack-focused test suite (ADR 0002), plus a provider-direct sign-in
   screen, 401 recovery, sign-out, and per-caller rate limiting
   (ADR 0003). **Remaining:** confirm the live provider round-trip on
   first deployment, refresh-token rotation, a shared-store limiter for
   multi-instance, and an admin surface for granting roles.
2. PostgreSQL adapter behind the existing `RunEngine`/memory interfaces,
   plus object storage for datasets and artifacts; migration tooling,
   backups, and restore drills (documented RPO/RTO).
   **Done:** run-engine Postgres adapter shipped and CI-enforced against
   Postgres 16; Supabase project `agentic-os` provisioned, RLS
   deny-by-default; sessions, memory, and published vault notes all moved
   behind the store, so the backend requires no local disk (ADR 0001 and
   its amendment), plus content-addressed dataset storage (ADR 0004), and
   backups with an executed restore drill — the suite destroys the
   database and rebuilds it through the operator scripts on every push,
   against both dialects, with measured times (ADR 0005).
   **Remaining:** a scheduled off-site backup job, which cannot live in
   this public repository without publishing user data (ADR 0005), and
   external object storage, which only becomes worthwhile above tens of
   megabytes.
3. Durable workflow execution: evaluate **Vercel Workflows for Python**
   directly against the run-engine contract (pause/resume/recovery)
   before committing to the abstraction; otherwise database-backed jobs
   with leases and heartbeats.
   **Done:** evaluated and declined in favour of database leases with
   heartbeats — a background worker advances runs with no browser open,
   crash recovery is lease expiry rather than a cleanup path, clients and
   workers can never execute the same task, and pause became durable
   server-side state so the control means the same thing in both modes
   (ADR 0006). **Remaining:** nothing starts the worker automatically,
   and Vercel's serverless runtime cannot host it, so hosted deployments
   there stay client-stepped.
4. Scalable analytics data plane: DuckDB or Polars for bounded local
   analysis, resumable uploads, dataset size/memory limits, partitioning
   and sampling, restricted-data egress controls.
   **Done:** content-addressed dataset storage (identical uploads stored
   once), file upload with client-side validation, dataset reuse by id,
   limits raised to 2 MB / 50,000 rows (ADR 0004). **Remaining:**
   DuckDB/Polars for larger-than-memory analysis, resumable uploads,
   partitioning and sampling.
5. Verified Vercel deployment against the hosted API; preview
   deployments per PR; rollback documented.
   **Done:** full-stack Vercel configuration (`api/index.py` ASGI entry
   + `vercel.json`), serverless hardening (Postgres reconnect,
   read-only-filesystem fallback), and a documented deploy/rollback
   procedure. **Remaining:** the import itself and the environment
   variables, which need the owner's credentials — no deployment has
   been made or claimed (see docs/VERCEL_DEPLOYMENT.md).
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
