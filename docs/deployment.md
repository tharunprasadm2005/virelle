# Deployment (local-first)

```bash
python -m venv .venv; .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"
cp .env.example .env   # set TASTEFLOW_SECRET
# place RAW_recipes.csv + RAW_reviews.csv in data/raw/
python scripts/inspect_dataset.py
python scripts/preprocess_data.py --mode full
python scripts/build_features.py
python scripts/build_ingredient_index.py --top-n 25000   # resumable
python scripts/build_recipe_name_index.py
python scripts/build_semantic_index.py                    # resumable, ~1.5GB out
python scripts/train_models.py
python scripts/evaluate.py --max-users 1000
python -m uvicorn backend.app.main:app --port 8000
```
Production notes: run uvicorn behind a reverse proxy (TLS + real rate limits),
set `TASTEFLOW_SECRET`, back up `tasteflow.db`, persist `data/processed/` +
`models/` (git-ignored build outputs). No Docker yet — add only when deploying
beyond localhost (documented decision, not an oversight).
