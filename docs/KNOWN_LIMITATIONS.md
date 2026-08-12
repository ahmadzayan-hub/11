# Known Limitations

Honest boundaries of the current release. None of these are hidden behind
placeholder controls — absent capabilities have no UI.

## Intelligence

1. The conversational agent is deterministic (command recognition +
   tone-styled acknowledgements); it is not an LLM chat.
2. The analytics pipeline is deterministic and descriptive: no
   statistical hypothesis testing, forecasting, optimization, or causal
   inference. Trend growth is not a forecast.
3. The optional Groq narrator only phrases verified facts and was not
   live-tested here (no credential); it falls back deterministically.
4. There is no autonomous "improve forever" loop. Runs are bounded;
   lessons accumulate as vault run logs for human review. Permanent 100%
   accuracy cannot honestly be promised by any AI system; deterministic
   calculations are exact for the operations implemented.

## Resolved since the first release

Sessions, transcripts, preferences, memory, and published knowledge are
now durable in the storage layer: a server restart no longer loses a
conversation, and in hosted mode (`DATABASE_URL`) the backend keeps no
required local files. Both behaviors are covered by tests
(`test_sessions_survive_an_application_restart`,
`test_hosted_mode_keeps_memory_in_the_database`).

## Platform

5. Authentication ships as an adapter (ADR 0002/0003): local mode is
   single-owner with no login; hosted mode verifies managed-provider
   JWTs with server-side roles, per-owner isolation, a sign-in screen,
   and per-caller rate limiting. Caveats: the live provider round-trip
   was never executed (this environment blocks HTTPS to the provider),
   so first-deployment sign-in must be confirmed once by hand; tokens
   are stored in browser storage without refresh rotation; and the rate
   limiter is per process, so multi-instance deployments need a shared
   store. There is no admin UI for granting roles — roles come from
   token claims or `AGENTIC_OS_DEFAULT_ROLE`.
6. Execution is client-stepped by default: runs advance while the Runs
   view is open. A background worker (`python scripts/worker.py`) can
   advance them server-side with no browser, using database leases with
   heartbeats (ADR 0006), but **nothing starts it automatically** and
   Vercel's serverless runtime has no process to run it in — hosted
   deployments there keep the client-stepped path. One worker advances
   one run at a time; parallelism means running more workers. A
   paused or interrupted run resumes from its durable state either way.
7. The repository is configured to deploy to Vercel as a full-stack
   project (static frontend + Python function). **No deployment has been
   performed or verified** — importing the repo and setting the
   credentials are owner steps. Without `DATABASE_URL` a deployment
   falls back to ephemeral per-instance storage. See
   docs/VERCEL_DEPLOYMENT.md.
8. Android support is a verified installable PWA; a native Capacitor
   project is documented but not shipped (no Android SDK available to
   build or test one honestly).
9. Obsidian integration is approval-gated write-back into a vault
    folder; reading/sync/retrieval from a vault is not implemented.
10. Interface language is English; the `language` preference is recorded
    but does not translate the UI. No RTL support yet.
11. Backups are on-demand: `scripts/backup.py` produces a verified,
    restorable backup (the drill in `tests/test_backup.py` destroys the
    database and rebuilds it on every push), but **nothing schedules
    it**, so the recovery point objective is "whenever it was last run".
    A nightly GitHub Actions job is deliberately not shipped — this
    repository is public and workflow artifacts would expose user data
    (ADR 0005). Supabase's automated daily backups cover Pro plans and
    above, not the free plan this project uses. Backup files are
    unencrypted JSON, the whole database is held in memory while one is
    written (fine at the 2 MB dataset limit, not at hundreds of
    megabytes), and in local mode `data/memory.json` lives outside the
    database and must be backed up separately.
12. Dataset ingestion is CSV only — uploaded as a file or pasted, up to
    2 MB and 50,000 rows, held in the database rather than object
    storage. XLSX, JSON, Parquet, and database connectors are not
    implemented, and analysis is in-memory (no DuckDB/Polars), so
    larger-than-memory datasets are out of scope.
