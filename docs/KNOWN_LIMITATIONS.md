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

## Platform

5. Single-user, local-first: no authentication, authorization, tenancy,
   or rate limiting. Do not expose beyond localhost as-is.
6. Sessions and transcripts live in server memory (runs, memory, and
   published reports are durable); a server restart starts a fresh
   session.
7. Runs advance while the Runs view is open (client-stepped execution);
   there is no background worker. A paused/interrupted run resumes from
   its durable state at any time.
8. Vercel hosts the static frontend only; the backend needs a persistent
   host (see docs/VERCEL_DEPLOYMENT.md). No deployment was made from the
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
