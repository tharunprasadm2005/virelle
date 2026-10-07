# Post-Phase-31 audit (read-only findings, 2026-10-06+)

Stack: FastAPI + vanilla static frontend (no build, no framework) + SQLite
(raw sqlite3, migration runner v1–v6) + joblib/FAISS artifacts. 35 routes,
6 product routers + research routes in main.py, 16 tests files (37 tests).

## Actual vs documented
- docs/api.md, database.md, testing.md (37), research.md all match code.
- deployment.md lacks the NLTK one-time download (only README has it).
- .env.example lacks RATE_LIMIT_AUTH_PER_MIN, CORS_ORIGINS, COOK_W_*, SEARCH_W_*.
- models/*.npy + *.index ARE gitignored (verified); tests/test_*.db+sqlite ignored.

## Backend debt (ranked)
1. **Circular STATE import**: 8 routers do `from backend.app.main import STATE`
   inside handlers; main imports routers at top. Works (deferred) but fragile;
   blocks reuse/testing of routers standalone.
2. **cook/matches full-table GROUP BY** over 6.35M-row name index per request —
   the single biggest measured-risk hotspot (rest is indexed).
3. **Per-request full-frame scans**: home() builds set_index ×3 + filters over
   522K/855K frames; taste bridge builds a 200K user-id set per uncached user.
4. Unused: `FileResponse` import (main.py), `python-multipart` dependency
   (no form/file endpoints), `_EPHEMERAL` has no TTL/lock (fine at demo scale).
5. JWT: `datetime.utcnow()` deprecated call; 7-day tokens + refresh, no rotation.
6. Rate limiter is in-process memory (resets on restart; fine single-node).
7. No pagination on `/api/recipes` beyond offset (added) — shelves fixed-size OK.
8. Errors: consistent JSON via HTTPException; 500 path logs with request id ✓.

## Frontend debt (vanilla decision: KEEP — see final report for justification)
- `alert()` for action errors; no toast; fetch has no timeout/AbortController.
- Inline `onclick` handlers (CSP-unsafe if headers ever added).
- `esc()` misses double-quotes (attribute-injection hardening gap, low risk:
  all interpolated values are ours or dataset text rendered into HTML bodies).
- Images lack dimensions (layout shift); missing focus-visible styles.
- Token in localStorage (XSS-sensitive; acceptable without stored XSS vectors —
  reviews render via esc()).
- Duplication: card rendering centralized ✓; page shells repeat header/nav
  boilerplate (~10 lines each — acceptable, no build system to share layouts).

## Security (no critical holes found)
SSRF guard covers loopback/private/link-local/IPv6 + redirects + size/timeout,
tested offline. Ownership enforced + tested. Hashing/JWT sane. Gaps: no reset
flow, no rotation, limiter is a backstop (documented), CORS default closed ✓.

## Performance risks (to measure in Phase 38)
cook GROUP BY; home full-frame scans; semantic lazy-load 800MB on first hit;
startup loads ~4.5GB joblibs (existing behavior, unchanged).

## Data/model
Research artifacts versioned (versions.json); ingredient/semantic indexes have
meta stamps; name sqlite lacks a version table (meta table exists ✓ actually —
has meta table with built_at; fine).
