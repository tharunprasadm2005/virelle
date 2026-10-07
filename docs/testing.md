# Testing matrix

`pytest tests/ -q` — 50 tests, all must pass. Isolated temp DBs per module
(autouse fixtures reset the shared `DB_PATH`); tiny labeled fixtures only
(`tests/fixtures/`, never real data, never metric claims).

Covered: pipeline (preprocess/temporal/aspect/baseline/hybrid/metrics/split),
research API (recipes, recs incl. cold-start, prefs, evolution, demo_users),
product (auth×5, prefs×3, search×3, interactions/favorites/home/taste/evolution,
meals/shopping/authz, collections, research, profile/password),
ingredients (5), knowledge (7), pantry (2), cook (2), imports (3), semantic (1).
E2E (manual, real data): register→onboard→cold recs→search→detail→like→
personalized→taste→plan→shopping→research (last full pass: Phase 9).
Frontend: no automated tests (static pages; verified manually per phase).
Missing (honest): load tests, security fuzz, frontend E2E harness.
