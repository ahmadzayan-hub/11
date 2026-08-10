# Architecture

```
Browser (React 19 + TS SPA, PWA)  ──HTTP/JSON──►  FastAPI adapter (server/app.py)
   Workspace · Runs · Memory                        │ sessions, validation, policy,
   Activity · Preferences                           │ security headers, no-store
                                                    ▼
                       ┌──────────────┬──────────────────────┬──────────────────┐
                       │ Agent core   │ Run engine           │ Model gateway    │
                       │ agent.py     │ server/runs.py       │ server/model_    │
                       │ (commands,   │ SQLite WAL, state    │ gateway.py       │
                       │ preferences, │ machines, approvals, │ deterministic ▸  │
                       │ memory)      │ artifacts            │ Groq (env-only)  │
                       └──────┬───────┴──────────┬───────────┴──────────────────┘
                              │                  │
                     data/memory.json    server/analytics.py (specialists)
                     (per-user, un-      └─ publish (approved) ─► vault/  ◄─ open
                      tracked by git)                              in Obsidian
```

## Boundaries

- **Domain core** (`agent.py`, `server/analytics.py`) is framework-free and
  fully testable without a network, browser, or credentials.
- **Run engine** (`server/runs.py`): durable SQLite (WAL) persistence for
  runs, tasks, approvals, and artifacts; explicit state machines with a
  central legal-transition table; client-stepped bounded execution
  (`advance` runs exactly one task), which yields honest pause/cancel and
  restart recovery without a background worker. SQLite over PostgreSQL is a
  deliberate local-first choice — the repository interface is small enough
  to swap when multi-user deployment justifies it.
- **Model gateway** (`server/model_gateway.py`): provider-neutral; the
  deterministic narrator is the default and the only provider used in
  tests/CI. Groq is configured exclusively via server-side env vars and can
  only phrase already-verified facts — every number comes from
  deterministic code.
- **API adapter** (`server/app.py`): validation (Pydantic), security
  headers, `Cache-Control: no-store` on `/api/*`, restricted CORS,
  path-aware static containment, safe errors.
- **Frontend** (`frontend/src/`): feature folders (chat, runs, memory,
  activity, preferences, commands, onboarding) + shared api/types/
  components/styles. No state library — one provider-scoped store.

## Data at rest

| Data | Location | Tracked by git |
| --- | --- | --- |
| Memory | `data/memory.json` | No (example file only) |
| Runs/tasks/approvals/artifacts | `data/agentic.db` (SQLite) | No |
| Published reports & run logs | `vault/` (Obsidian-compatible) | No |
| Settings | `config.json` | Yes (no secrets) |

## Key decisions

1. **Client-stepped runs** instead of a worker queue: honest progress,
   pause, cancel, and restart recovery with zero infrastructure; the
   engine API would keep the same shape over a real queue.
2. **Deterministic analytics** instead of LLM-calculated numbers: claims
   trace to calculation ids and are independently re-verified by the
   Validation Expert stage.
3. **Approval bound to content hash**: publishing re-hashes the artifact
   and refuses if it changed after the approval was requested.
