import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Preprocess REAL data: data/raw/ -> data/processed/. No synthetic data."""
import argparse
import sys
import pandas as pd
from src import config
from src.data import loader
from src.data import preprocess as P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default=config.DATA_MODE, choices=["full", "sample"])
    args = ap.parse_args()
    try:
        recipes_raw, inter_raw, meta = loader.load_raw()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(2)
    print("Loaded:", meta["recipe_file"], meta["interaction_file"])
    print("Column mapping (recipes):", meta["recipe_map"])
    print("Column mapping (interactions):", meta["interaction_map"])
    recipes = P.preprocess_recipes(recipes_raw)
    inter = P.preprocess_interactions(inter_raw, valid_recipe_ids=set(recipes["recipe_id"]))
    print(f"Preprocessed: {len(recipes)} recipes, {len(inter)} interactions")
    if args.mode == "sample":
        recipes, inter = P.sample_real_subset(recipes, inter)
        print(f"Sample mode (REAL subset): {len(recipes)} recipes, {len(inter)} interactions")
    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    recipes.to_csv(config.DATA_PROCESSED_DIR / "recipes_processed.csv", index=False)
    inter.to_csv(config.DATA_PROCESSED_DIR / "interactions_processed.csv", index=False)
    report = {"n_recipes": len(recipes), "n_interactions": len(inter),
              "n_users": int(inter["user_id"].nunique()), "mode": args.mode, **meta}
    pd.Series(report).to_json(config.DATA_PROCESSED_DIR / "preprocess_report.json", indent=2)
    print("Wrote data/processed/recipes_processed.csv + interactions_processed.csv")


if __name__ == "__main__":
    main()
