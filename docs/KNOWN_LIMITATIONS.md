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

5. Authentication ships as an adapter (ADR 0002): local mode is
   single-owner with no login; hosted mode verifies managed-provider
   JWTs with server-side roles and per-owner isolation. **No sign-in UI
   exists yet** — a hosted deployment must obtain tokens through its own
   provider front door. Rate limiting is still absent. Treat a hosted
   deployment as pre-production until the sign-in flow lands.
6. Runs advance while the Runs view is open (client-stepped execution);
   there is no background worker. A paused/interrupted run resumes from
   its durable state at any time.
7. Vercel hosts the static frontend only; the backend needs a host that
   can hold TCP connections to PostgreSQL (see
   docs/VERCEL_DEPLOYMENT.md). No deployment was made from the
   implementation environment.
9. Android support is a verified installable PWA; a native Capacitor
   project is documented but not shipped (no Android SDK available to
   build or test one honestly).
10. Obsidian integration is approval-gated write-back into a vault
    folder; reading/sync/retrieval from a vault is not implemented.
11. Interface language is English; the `language` preference is recorded
    but does not translate the UI. No RTL support yet.
12. Dataset ingestion is CSV (pasted text, ≤250 KB / ≤5000 rows); XLSX,
    JSON, Parquet, databases, and file upload are not implemented.
