# Baseline analysis (original project: `baseline_original/`)

Kept untouched as the reference implementation. Summary from code inspection:

- **App**: `baseline_original/data/Scripts/recommender_app.py` (~657 lines) — interactive CLI,
  SQLite (`recommendations.db`), pickle cache. No web API/frontend.
- **Pipeline**: `preprocess_recipes_and_build_initial_models.py` (~494 lines) + notebooks;
  hardcoded `BASE_DIR = C:\Users\dell\DSProject1` (non-portable — fixed in our code via
  relative `src/config.py` paths).
- **Recipe representation**: `content_features` = name + description + ingredients + tags;
  TF-IDF (≤20k features, 1–2 grams) + cosine; KMeans clustering; RapidFuzz dietary flags;
  nutrition list exploded to 7 columns; `minutes` capped at 1440.
- **User representation**: dietary booleans + cuisines + ingredients + max cook time (new users);
  rated-item set + SVD latent factors (existing users).
- **CF**: scikit-surprise SVD on ratings 1–5 (dedup keep-last, drop rating 0, users ≥5 / recipes ≥3).
- **Hybrid**: `0.7·CF + 0.3·CB` (CB cosine scaled to 1–5); popularity fallback for cold start.
- **What it ignores**: review text (loaded, never mined) and timestamps (only used for dedup)
  — exactly the two signals our additions exploit.
- **Limitations**: surprise has no modern-Windows wheels; no evaluation metrics; no temporal
  weighting; no aspect modelling; no API/UI; absolute paths.

Our `src/recommender/baseline.py` preserves this algorithm (same alpha, same fallbacks) with
`TruncatedSVD` replacing surprise (same matrix-factorisation family — documented in
`docs/METHODOLOGY.md`).
