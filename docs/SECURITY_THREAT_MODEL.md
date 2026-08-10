# Security Threat Model

Scope: local-first, single-user application (CLI + web UI + FastAPI on
localhost). There is no authentication layer — adding one is the first
step before any multi-user or hosted deployment (see limitations).

## Assets

User memory (`data/memory.json`), run data and reports (`data/agentic.db`,
`vault/`), settings (`config.json`), the optional `GROQ_API_KEY`.

## Trust boundaries and controls

| Threat (OWASP LLM/Agentic aligned) | Control implemented | Verified by |
| --- | --- | --- |
| Prompt/goal injection via dataset content | Analytics stages are deterministic code; dataset text is data, never instructions; the model narrator receives only computed facts | design + tests |
| Unapproved side effects (excessive agency) | The only side-effecting stage (vault publish) is server-enforced behind an approval bound to the artifact SHA-256; a changed artifact invalidates approval | `tests/test_runs.py` |
| Lost updates / data loss | Cross-session memory reload under a server lock; honest failure messages on failed writes; SQLite WAL transactions | `tests/test_api.py`, `tests/test_utils.py` |
| Path traversal | Resolved-path `is_relative_to` containment for static files | `tests/test_api.py` |
| Sensitive data caching | `Cache-Control: no-store` on all `/api/*` responses | `tests/test_api.py` |
| Clickjacking / MIME sniffing | `X-Frame-Options: DENY`, `nosniff`, referrer & permissions policies (server + Vercel headers) | header test |
| Secret exposure | No secrets in the repo; provider keys are env-only, never logged or sent to the browser; `.env.example` has placeholders only | repo scan, code review |
| Unbounded loops / cost | Runs have a fixed bounded stage list; datasets capped (250 KB / 5000 rows); model calls capped (1 per run, 220 tokens, 12 s timeout) | code + tests |
| Stack-trace disclosure | Global exception handler returns a generic message | `server/app.py` |
| Privacy in git history | Runtime data (`memory.json`, `agentic.db`, `vault/`) untracked and ignored; note: `data/memory.json` existed in history as `{}` only — no personal data was ever committed | git log |

## Known gaps (explicit)

1. No authentication/authorization — do not expose the server beyond
   localhost as-is.
2. No rate limiting (single-user assumption).
3. No CSRF tokens (no cookie-authenticated state; CORS is restricted).
4. Groq path could not be live-tested here (no key); its failure handling
   is defensive-by-construction and falls back deterministically.
