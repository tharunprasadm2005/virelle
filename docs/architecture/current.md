# Current architecture (frozen 2026-10-06, Phase 0 checkpoint)

No Git repository exists for this project, so this document plus the
immutable model artifacts below constitute the freeze checkpoint.

## Freeze state
- Tests: **16/16 passing** (`pytest tests/ -q`)
- Evaluation (real Food.com, `experiments/ablation_results.csv`, K=10, 1000 users):
  baseline HR 0.001 / temporal HR 0.001 / aspect HR 0.002 / full HR 0.002
  (P@10 0.0001/0.0001/0.0002/0.0002; NDCG@10 0.00029/0.00030/0.00095/0.00095)
- Artifacts: `models/cf_svd.joblib` (84.5MB), `models/recommenders.joblib` (~3.8GB),
  `models/tfidf*.joblib` (~338MB), processed CSVs in `data/processed/`
- Dataset: `data/raw/RAW_recipes.csv` (522,517 rows), `RAW_reviews.csv` (1,401,982 rows)
- No developer absolute paths in `src/`, `backend/`, `scripts/` (verified by grep)
- `baseline_original/` untouched; research endpoints unchanged

## Layers
- **Product:** FastAPI routers in `backend/app/api/` (auth, profile, interactions,
  taste/home, search, mealplan, shopping, research) + 11 static pages in `frontend/`
- **Bridge:** `src/recommender/taste.py` (effective ids, implicit ratings, ephemeral
  per-user engine views; engine logic itself untouched)
- **Engine (research):** `src/recommender/{baseline,temporal,aspect_model,hybrid,
  explanations,evaluate}.py`; pipeline `scripts/`; metrics `experiments/`
- **App data:** SQLite `tasteflow.db` (6 tables, see `backend/app/db.py`);
  schema evolution via `backend/app/migrations.py` (version table, ordered SQL)
- **Config:** `src/config.py` (relative paths) + `.env` / `.env.example`

## Migration strategy (decision)
No SQLAlchemy/Alembic: the backend uses raw sqlite3 with 6 tables and the
scale is single-node. A full ORM migration would be a massive rewrite for zero
behavioral gain. Instead: `schema_migrations(version)` + ordered SQL migrations
in `backend/app/migrations.py`, applied at startup. Revisit only if we outgrow
SQLite (concurrent writers) — documented in `docs/roadmap.md`.
