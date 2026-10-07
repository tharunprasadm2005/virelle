# Security notes

- Passwords: bcrypt (SHA-256 pre-hash for >72B), never stored/returned in plain.
- JWT HS256, 7-day expiry, `POST /api/auth/refresh`; secret via `TASTEFLOW_SECRET`
  (dev default is long but public — set a real one in production).
- Ownership: every user-owned query scopes `user_id=current_user`; cross-user
  access returns 404 (no oracle). Verified by tests (pantry/shopping/collections).
- Injection: all SQL parameterized; Pydantic validation on inputs (length caps).
- SSRF: URL import allows http(s) only, requires public-IP DNS, 10s timeout,
  2MB cap, redirect re-check, desktop UA. Tested without network.
- Auth backstop rate limit (env `RATE_LIMIT_AUTH_PER_MIN`, default 60/IP/min);
  real brute-force defense belongs at the reverse proxy (documented limitation).
- CORS: same-origin by default; allow-list via `CORS_ORIGINS` env when needed.
- Secrets: none in frontend; `.env.example` documents all vars.
- Known gaps (honest): no password-reset flow, no refresh rotation, no audit log,
  SQLite file permissions rely on host. See roadmap.
