# Virelle roadmap (from Phase 0 analysis)

Done (frozen): product v1 (auth→planner→shopping), engine, honest evaluation.
Each phase: implement → tests → E2E → docs → report.

- [x] Phase 0 — freeze, migration mechanism, arch docs
- [x] Phase 1 — ingredient intelligence (parser eval + normalized layer)
- [x] Phase 2 — ingredient knowledge / allergens / categories
- [x] Phase 3 — pantry system
- [x] Phase 4 — "What can I cook?" (coverage + personalization ranking)
- [x] Phase 5 — shopping intelligence (merge, pantry-aware)
- [x] Phase 6 — semantic search (MiniLM + FAISS sidecar, TF-IDF kept)
- [x] Phase 7 — hybrid retrieval + product ranking (documented weights)
- [x] Phase 8/9 — USDA nutrition layer + nutrition-aware ranking (preferences only)
- [x] Phase 10 — recipe URL import (SSRF-guarded)
- [x] Phase 11 — collections/cookbooks
- [x] Phase 12 — cook mode (cooked event feeds pipeline)
- [x] Phase 13 — impression/open event tracking (skips derived, never stored)
- [x] Phase 14/15 — short-term intent (session-only) + fatigue control
- [x] Phase 16 — product-signal explanations (deterministic, grounded)
- [x] Phase 17 — DECIDED: postpone LLM assistant (see note below; no code)
- [x] Phase 18-24 — hardening (logging, auth backstop+refresh, pagination, CORS-config, deep health), API quality, caching decision (in-process; Redis refused), jobs decision (APScheduler path documented, manual rebuilds), security audit, observability (request ids/timing)
- [x] Phase 25/26 — frontend terminology (ML terms research-only) + state audit (loading/empty/error/unauth/no-result states on all pages)
- [x] Phase 27-31 — testing matrix (37 green), research separation (`docs/research.md`), versioning (`models/versions.json` + research summary), final audit

## Phase 17 decision (assistant postponed)
Every listed assistant use-case ("what can I cook", "high-protein dinner",
"plan 5 dinners", "replace X", "from these ingredients") is already served by
deterministic endpoints (cook/matches, search+filters, mealplan/generate,
shopping, knowledge synonyms). An LLM would add latency, cost, hallucination
risk, and infra for zero uncovered user problem — violating strict rules 9–10.
Reserved slot if ever revisited: intent-parse → call the deterministic APIs →
render results; the LLM must never rank or invent recipes. Revisit only on a
concrete unsupported request class.

Out (explicit): Postgres/Redis/Celery/Qdrant/Meilisearch/native apps/social —
revisit only on measured need. No paid LLM APIs in core paths.

## React migration (page-by-page, started)
- [x] Scaffold `frontend-react/` (Vite + React 18 + TypeScript strict, proxy /api → :8000)
- [x] Shared typed client (`api.ts` mirrors backend contracts), Toast, RecipeCard, Layout
- [x] Auth page (login/register/demo) + Home page (greeting, search, intent, recs, shelves, saved, events)
- [x] Discover + Recipe (detail/actions/feedback/cook-mode/collections) + Pantry + Cook + Meals + Shopping + Taste + Profile + Research + Onboarding + Landing
- [x] Claymorphism/neomorphism design system (new `index.css`), modern typography
- [x] `tsc --noEmit` clean, `vite build` clean
- Backend API contracts frozen — no backend changes for this migration.
