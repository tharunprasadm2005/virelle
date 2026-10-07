import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Build + cache features: TF-IDF, CF-SVD, aspect tables, temporal cache."""
import sys
import joblib
import pandas as pd
from src import config
from src.data import features as F
from src.recommender import aspect_model as A


def main():
    try:
        recipes = pd.read_csv(config.DATA_PROCESSED_DIR / "recipes_processed.csv")
        inter = pd.read_csv(config.DATA_PROCESSED_DIR / "interactions_processed.csv")
    except FileNotFoundError:
        print("ERROR: processed data missing. Run scripts/preprocess_data.py first (requires real data in data/raw/).")
        sys.exit(2)
    inter["date"] = pd.to_datetime(inter["date"], errors="coerce")
    print("Building TF-IDF...")
    vec, mat = F.build_tfidf(recipes)
    print("Building CF (TruncatedSVD)...")
    cf = F.build_cf(inter)
    print("Building aspect tables from real review texts...")
    ua, ra = A.build_aspect_tables(inter)
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vec}, config.MODELS_DIR / "tfidf.joblib")
    joblib.dump({"matrix": mat, "recipe_ids": recipes["recipe_id"].to_numpy()}, config.MODELS_DIR / "tfidf_matrix.joblib")
    joblib.dump(cf, config.MODELS_DIR / "cf_svd.joblib")
    ua.to_csv(config.DATA_PROCESSED_DIR / "user_aspects.csv", index=False)
    ra.to_csv(config.DATA_PROCESSED_DIR / "recipe_aspects.csv", index=False)
    print(f"Cached models/ + aspect tables ({len(ua)} users, {len(ra)} recipes with review aspects).")


if __name__ == "__main__":
    main()
