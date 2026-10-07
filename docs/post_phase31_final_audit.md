# Post-Phase-31 final audit (stabilization complete)

## 1-4. Architectures
- **Existing/frontend:** vanilla static (11 pages + 45-line shared client + CSS),
  no build, served by FastAPI. **Decision: KEEP — Next.js migration NOT justified**
  (see §20).
- **Backend:** routers → deps (STATE/rmap/rname/ids accessors) → sqlite helpers →
  engine bridge. Circular import eliminated; no service/repository split (correct
  call at this size — routers are thin, SQL is simple, a repository layer would
  add files without removing coupling).
- **Database:** 12 tables, migrations v1–v6 tested (fresh/idempotent/ordered/FK).

## 5-6. API/page inventory
38 product routes + 10 research routes (see docs/api.md). All 11 pages work;
every frontend `api()` call is contract-tested against the route table.

## 7-10. Bugs/security/performance fixed
- Fixed: circular STATE import; cook full-table GROUP BY → bounded indexed query;
  per-request set_index/tolist scans → startup-built caches; 500-path NameError
  (caught by suite); test DB cross-contamination (autouse fixtures everywhere);
  SSRF edge forms verified (decimal/octal/IPv6/0.0.0.0); `esc()` quote hardening;
  fetch timeouts; toasts replacing alerts; focus styles; touch targets.
- Security: no critical holes; backstop limiter env-tunable; refresh added;
  CORS closed by default; SSRF regression tests green.
- Measured (real data): cook ~4s first call (bounded; see debt), home ~2.3s,
  hybrid steady 0.76s (19s first-hit semantic load → lifespan warmup thread),
  taste 0.16s. No Redis/caching infra added — unjustified.

## 11-12. Improvements
Backend: deps.py boundary, caches, logging w/ request ids, deep health,
pagination offset, refresh, CORS config. Frontend: timeout/toast/esc/focus/
touch/contract safety. No engine/model changes; ablation CSV untouched.

## 13-17. Tests/build/deploy/E2E
- Before: 37. After: **50/50 green** (+edges, migrations, contract, journeys).
- E2E (real data): register→onboard→cold→search→detail→actions→personalized→
  taste→plan→shop→research all pass; stabilization loop re-verified post-change.
- Build: no build step (static); clean-env: requirements cover all imports,
  .env.example synced, no absolute paths, no secrets in repo.
- Deployment verified via TestClient + earlier live uvicorn runs.

## 18-19. Debt & limitations (honest)
- cook/matches ~4s on broad pantries (bounded; next step: per-name count table).
- First semantic search pays model+index load (warmup thread covers servers).
- No password-reset flow; no refresh rotation; limiter is a backstop (proxy owns
  real defense); SQLite single-node (correct for now).
- No browser E2E harness (Phase 50 verdict: unjustified here — no node/browsers
  guaranteed, offline env; static contract test + TestClient journeys instead).
- python-multipart removed; FileResponse import removed; utcnow fixed.

## 20. Next.js verdict
**Current frontend architecture is sufficient after refactoring; Next.js
migration is not justified by measured requirements.** Reasons: 11 pages share a
45-line client with zero build/deploy cost; routing/state needs are trivial
(full-page navigations, localStorage token); no measured perf problem the
framework would fix; migration would add Node toolchain + rewrite risk for no
user-visible gain. Revisit only if: SPA-style state, offline-first, or app-store
presence becomes a requirement.
