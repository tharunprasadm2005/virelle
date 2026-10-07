# Dataset

Source: https://www.kaggle.com/datasets/irkaal/foodcom-recipes-and-reviews (Food.com Recipes and Reviews).
Place files in `data/raw/` as `RAW_recipes.csv` + `RAW_interactions.csv` and run
`python scripts/inspect_dataset.py` for actual row counts/columns/missingness
(the script reports reality rather than asserting it here).

Final evaluation protocol: `DATA_MODE=full` on this dataset with the per-user temporal
split in `scripts/evaluate.py`. `DATA_MODE=sample` selects a deterministic REAL subset
(`SAMPLE_N_RECIPES`/`SAMPLE_N_INTERACTIONS`) for development only.
