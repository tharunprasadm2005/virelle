# Virelle — Recipes that learn your taste
### Product built on: Adaptive Personalized Recipe Recommendation System Using Preference Evolution and Review-Aspect Learning

> Formerly **TasteFlow**. Internal identifiers (`tasteflow.db`, `TASTEFLOW_SECRET`,
> `TASTEFLOW_DB`, the `tasteflow-demo` password) were deliberately left unchanged
> for backward compatibility — see `docs/brand-final.md`.

We extend a conventional personalized recipe recommendation system by incorporating
temporal preference evolution and review-aspect-based preference signals, and evaluate
whether these additions improve recommendation quality. Baseline: `baseline_original/`
(hybrid TF-IDF + SVD-CF, preserved in `src/recommender/baseline.py`).

**The system is developed and evaluated using the Food.com Recipes and Reviews dataset.**
No synthetic data is used for training, evaluation, or results — tiny synthetic fixtures
exist only under `tests/fixtures/` for unit tests ("TEST FIXTURE — NOT PROJECT DATA").

---
## PRODUCT FEATURES (Virelle)
- Accounts + onboarding (diet, cuisines, priorities, avoided ingredients, max time)
- Home with personalized picks, popularity/quick/healthy shelves, saved recipes
- Real Food.com catalog (522K recipes, real photos where the dataset provides them)
- Recipe pages: like / dislike / save / cooked / 1–5 ratings / taste-note reviews
- Every interaction becomes a real personalization signal (temporal recency included)
- My Taste: interest bars, review-derived likes/dislikes, earlier-vs-recent evolution
- Personalized search, Discover sections with diet/time filters
- Weekly meal planner (generate my week: saved-first, no repeats, respects avoids/dislikes)
- Shopping list (add from any recipe's real ingredients, check off, clear done)
- Pantry + What-can-I-cook (coverage × taste ranking, missing → shopping)
- Ingredient intelligence (parsed quantities, categories, allergen/diet estimates)
- Semantic + hybrid search (MiniLM/FAISS sidecar; TF-IDF preserved)
- Recipe URL import (attributed, SSRF-guarded), collections/cookbooks, cook mode
- Nutrition (listed values + goals-as-preferences; USDA snapshot path documented)
- Demo account ("Tharun Demo", linked to Food.com history 269575) from the login page

## RESEARCH / EVALUATION FEATURES (academic, unchanged)
- Baseline / +Temporal / +Aspect / Full ablation (`scripts/evaluate.py`)
- Temporal per-user split (train older, test recent liked); P@K/R@K/NDCG@K/HR@K
- Measured: aspect signals ~2× baseline hit-rate; temporal alone neutral (see `docs/EXPERIMENTS.md`)
- Faculty view: `/research.html` + `/api/research/summary` + `/api/demo_users`
- Original research dashboard endpoints (`/api/recommendations/{id}`, `/api/preferences/*`) intact
---

## Setup
```bash
git clone <project>; cd <project>
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"  # one-time, for ingredient parsing
cp .env.example .env   # or copy manually on Windows
```

## Dataset setup (REAL data, required)
1. Download https://www.kaggle.com/datasets/irkaal/foodcom-recipes-and-reviews
2. Place files in `data/raw/` as `RAW_recipes.csv` and `RAW_interactions.csv`
3. `python scripts/inspect_dataset.py` — verifies real columns/rows
- Missing files → every entry point prints: *"Food.com dataset not found. Download the
  dataset from Kaggle and place RAW_recipes.csv and RAW_interactions.csv in data/raw/."*
- `DATA_MODE=sample` (default) uses a deterministic REAL subset for dev;
  `DATA_MODE=full` uses everything for final training/evaluation.

## Run pipeline (real data)
```bash
python scripts/preprocess_data.py --mode full
python scripts/build_features.py
python scripts/train_models.py
python scripts/evaluate.py     # ablation -> experiments/ablation_results.csv + reports/figures/
uvicorn backend.app.main:app --reload   # Virelle at http://127.0.0.1:8000
```
Open http://127.0.0.1:8000 → sign up (or "Try the demo account") → onboarding →
home. Research view: http://127.0.0.1:8000/research.html.

## API (product)
`POST /api/auth/register|login`, `GET /api/auth/me`, `GET|PUT /api/profile`,
`GET|PUT /api/preferences`, `GET /api/home`, `GET /api/taste`, `GET /api/taste/evolution`,
`GET /api/recipes/search`, `GET /api/discover`, `POST /api/interactions/{id}`,
`GET /api/favorites`, meal-plans, shopping-list, `GET /api/research/summary`.
Research endpoints (`/api/recommendations/{user_id}`, `/api/preferences/{user_id}/*`,
`/api/demo_users`, `/api/dataset/status`) are unchanged.

## Tests (fixture only, no metric claims)
```bash
pytest -q
```

## API
`GET /api/recipes`, `/api/recipes/{id}`, `/api/recommendations/{user_id}?k=10&mode=full`,
`/api/preferences/{user_id}`, `/api/preferences/{user_id}/evolution`,
`/api/preferences/{user_id}/aspects`, `/api/recommendations/{user_id}/explanations`,
`/api/dataset/status`, `/api/health`.

## Demo (5–10 min, real data)
1. `/api/dataset/status` shows real files present (522,517 recipes / 1.4M reviews).
2. Demo user `269575` (shift ≈ 0.38, 34 old + 23 recent interactions):
   old = desserts/fried chicken era (Pavlova, Kentucky Fried Chicken, Cherry Cheesecake);
   recent = Indian-vegetarian era (Mattar Paneer, Vegetable Makhani, Shoarma Spice Mix);
   review aspects: quick +0.92, easy +0.89, healthy +0.80, taste +0.71.
3. Show `/api/preferences/269575/evolution` (shift) → `/aspects` (likes/dislikes).
4. Compare `mode=baseline` vs `mode=full` at `/api/recommendations/269575?k=10`
   + per-part scores + explanations generated from actual signals.
5. Show `experiments/ablation_results.csv` + `reports/figures/` (aspect/full ≈ 2×
   baseline hit-rate; temporal neutral — reported honestly in `docs/EXPERIMENTS.md`).

See `docs/` for methodology, architecture, experiments, limitations.
