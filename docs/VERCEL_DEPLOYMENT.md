# Vercel Deployment

## What ships today

`vercel.json` builds and serves the **frontend** (static SPA + PWA) with
SPA rewrites and security headers:

```bash
npm i -g vercel@latest   # or pin in CI
vercel pull && vercel build && vercel deploy --prebuilt
```

## The honest constraint

The backend is FastAPI with **stateful, durable local persistence**
(SQLite in WAL mode, a shared memory file, and vault file writes).
Vercel functions are stateless with an ephemeral filesystem, so deploying
this backend to Vercel functions would silently lose runs, memory, and
published reports — a data-loss defect, not a deployment.

A frontend-only Vercel deployment boots to the app's honest offline/boot
error state ("Cannot reach the Agentic OS server") unless an API origin
is provided.

## Supported production path

1. Host the backend on a server platform (Fly.io, Railway, Render, a VM):
   `uvicorn server.app:app --host 0.0.0.0`.
2. Set `DATABASE_URL` to the provisioned Supabase PostgreSQL (project
   `agentic-os`, session-pooler string from the dashboard — see
   `.env.example` and `docs/adr/0001-database.md`). Runs, tasks,
   approvals, and artifacts then persist in hosted Postgres, verified by
   the CI Postgres suite.
3. Set the API origin at frontend build time: `VITE_API_BASE=https://api.example.com`.
4. Add the Vercel domain to `AGENTIC_OS_ALLOWED_ORIGINS` on the backend.
5. Keep `GROQ_API_KEY` and `DATABASE_URL` on the backend host only.
6. Deploy the frontend to Vercel with the config in this repo.

Remaining host-local state (why a persistent disk is still recommended):
sessions/transcripts (in-memory), `data/memory.json`, and vault files.
Moving those to the hosted database is the next roadmap step before a
fully stateless backend.

Migrating persistence to PostgreSQL + object storage (per the V2 master
prompt) is the prerequisite for an all-Vercel architecture; the
`RunEngine` interface is deliberately narrow to make that adapter swap
tractable.

## Deployment status

No Vercel deployment was performed from this environment: deploying the
frontend alone without a reachable backend would publish a non-functional
app, and backend credentials/hosting were not provisioned. This is the
precise blocker, reported per the master prompt rather than papered over.
