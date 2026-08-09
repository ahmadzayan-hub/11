# Agentic OS — UI/UX Audit and Transformation Plan

Date: 2026-08-09 · Branch: `claude/agentic-os-final-project-53j6ql` · Baseline commit: `ede0ed5`

## 1. Current Architecture (before transformation)

- Pure Python 3 command-line application, standard library only.
- `main.py` runs a blocking `input()` loop in a terminal; `agent.py` holds all
  behaviour (commands, preferences, history, memory); `utils.py` handles
  config loading, JSON persistence, and validation.
- State: session history in memory; persistent memory in `data/memory.json`;
  settings in `config.json`.
- 44 passing `unittest` tests; no frontend, no web server, no JavaScript, no
  lockfiles, no CI. Working tree clean at baseline.

Baseline verification performed: `python -m unittest discover tests` → 44/44
OK; `python main.py` starts and handles all documented commands.

## 2. Existing Strengths

- The Agent class is small, well-tested, and fully decoupled from I/O — ideal
  for wrapping with a web API without duplication.
- Deterministic, local behaviour: no external AI service, no credentials.
- Error handling already covers empty input, unknown commands, and corrupt or
  missing files.
- Documentation (README, user guide) accurately matches behaviour.

## 3. Critical Problems (as a user-facing product)

1. Terminal-only: unusable for non-technical users; no visual identity.
2. Commands must be memorized; no discovery beyond `/help` text.
3. Memory and preferences are invisible — no way to see current state at a
   glance or manage entries without typing exact keys.
4. No session status, activity feedback, or error surfaces beyond plain text.
5. No mobile or accessibility story of any kind (screen readers get a raw
   TTY stream).

## 4. User-Experience Gaps

- No onboarding: first-run users see one welcome line.
- No empty/loading/error/offline states (concepts don't exist in a TTY).
- No confirmation before destructive actions (`/forget all`, `/clear`).
- No copy, timestamps, retry, or history browsing affordances.

## 5. Accessibility Gaps

- None of WCAG 2.2 applies to a TTY app, which is itself the gap: no
  semantics, focus management, contrast control, or reduced-motion support
  can exist until there is a UI.

## 6. Performance Risks (for the planned web layer)

- Risk: heavy UI frameworks/fonts/icon packs would be the only threat to
  Lighthouse targets — the backend is in-process and instant.
- Mitigation chosen: system font stack (zero font requests), inline SVG icon
  set, no CSS framework, no state library, single small route bundle.

## 7. Security & Privacy Concerns

- `data/memory.json` stores plain-text user memory; must stay out of logs,
  be clearly explained, and be deletable from the UI.
- New API surface must validate input length/shape, hide stack traces,
  restrict CORS, and add no secrets (there are none today — keep it that way).
- Destructive endpoints (clear history/memory) need explicit UI confirmation.

## 8. Proposed Architecture

```
Browser (React + TypeScript + Vite SPA, CSS design tokens)
   │  JSON over HTTP (typed contracts, timeouts, abort, central error handling)
   ▼
FastAPI adapter (server/app.py) — sessions, validation, safe errors, CORS,
static hosting of the built SPA
   │  direct in-process calls (no logic duplicated)
   ▼
Existing Agent class (agent.py) + utils.py + data/memory.json  ← unchanged
```

- The adapter maps structured operations onto the Agent's already-tested
  command surface (`/remember`, `/forget`, `/set`, `/clear`) and returns
  fresh state snapshots, so no business logic exists in TypeScript.
- The CLI (`python main.py`) keeps working unchanged, stdlib-only.

Stack rationale: repository contained no frontend, so the preferred stack
(React/TS/Vite + FastAPI) applies. Tailwind was rejected in favour of ~600
lines of token-based CSS — smaller, no build plugins, full design control.
No router: four lightweight panels toggle inside one shell; route-level code
splitting would add loading states with no measurable payload benefit
(single JS bundle is ~60 KB gzipped).

## 9. Implementation Priorities

1. FastAPI adapter + API tests (foundation; nothing ships untested).
2. App shell: navigation, status, theme, responsive drawer.
3. Chat workspace: composer, states, retry, quick actions, palette.
4. Memory & preferences management with confirmations.
5. Activity feed (real events only), onboarding, help.
6. Accessibility pass, responsive verification, performance measurement.
7. Documentation.

## 10. Measurable Acceptance Criteria

- All Python tests pass (existing 44 + new API tests); frontend unit tests
  and the end-to-end main journey pass; `tsc --noEmit` and `vite build` clean.
- Main journey works: open session → send message → save memory → change
  preference → view history → clear history with confirmation → end session.
- Layouts verified at 320/375/768/1024/1440 px with no horizontal overflow.
- Full keyboard operation; dialogs trap focus and close on Escape; WCAG 2.2
  AA contrast; reduced-motion respected.
- Lighthouse (production build): Performance ≥ 95, Accessibility 100,
  Best Practices ≥ 95; LCP < 2.5 s, CLS < 0.1, INP < 200 ms — measured, with
  any shortfall reported honestly.
- No secrets, no fake features, no dead controls; docs match the final app.

## 11. Verified Results (measured on the final build)

- Tests: Python 59/59 · frontend unit 18/18 · Playwright e2e 15/15
  (1 desktop-only check skipped on the mobile project by design);
  `tsc --noEmit` clean; production build clean (69.2 KB gzipped JS,
  4.5 KB gzipped CSS, system fonts, no external requests).
- Lighthouse 13.x, mobile emulation, production server: **Performance 97 ·
  Accessibility 100 · Best Practices 100 · SEO 100**; LCP 2.3 s · CLS 0 ·
  TBT 0 ms. (The experimental "agentic-browsing" category scores 67 — it
  recommends publishing an llms.txt file, which is out of scope for a
  local application.)
- Automated axe-core WCAG 2.2 A/AA scans pass on every view and dialog in
  both viewports; the one real finding it caught during development
  (faint-text contrast 4.16:1 at 12 px) was fixed by darkening the token
  to ≥ 4.78:1 on every light surface.
- Main journey (open session → message → save memory → change preference →
  view history → clear history with confirmation → end session → new
  session) passes on desktop (1440 px) and mobile (375 px) with zero
  browser console errors; horizontal-overflow checks pass at 320, 375,
  768, 1024, and 1440 px.
