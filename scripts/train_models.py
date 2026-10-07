import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Train recommenders on REAL processed data and persist state."""
import sys
import joblib
import pandas as pd
from src import config
from src.recommender.baseline import BaselineRecommender
from src.recommender.hybrid import AdaptiveRecommender


def main():
    try:
        recipes = pd.read_csv(config.DATA_PROCESSED_DIR / "recipes_processed.csv")
        inter = pd.read_csv(config.DATA_PROCESSED_DIR / "interactions_processed.csv")
        ua = pd.read_csv(config.DATA_PROCESSED_DIR / "user_aspects.csv")
        ra = pd.read_csv(config.DATA_PROCESSED_DIR / "recipe_aspects.csv")
    except FileNotFoundError:
        print("ERROR: run scripts/preprocess_data.py and scripts/build_features.py first.")
        sys.exit(2)
    inter["date"] = pd.to_datetime(inter["date"], errors="coerce")
    vec = joblib.load(config.MODELS_DIR / "tfidf.joblib")["vectorizer"]
    mat = joblib.load(config.MODELS_DIR / "tfidf_matrix.joblib")["matrix"]
    cf = joblib.load(config.MODELS_DIR / "cf_svd.joblib")
    base = BaselineRecommender(recipes, inter, vec, mat, cf)
    adapt = AdaptiveRecommender(base, recipes, inter, ua, ra)
    joblib.dump({"baseline": base, "adaptive": adapt}, config.MODELS_DIR / "recommenders.joblib")
    import json
    from datetime import datetime, timezone
    versions = {"trained_at": datetime.now(timezone.utc).isoformat(),
                "n_recipes": len(recipes), "n_interactions": len(inter),
                "weights": {"w_baseline": config.W_BASELINE, "w_temporal": config.W_TEMPORAL,
                            "w_aspect": config.W_ASPECT, "hybrid_alpha": config.HYBRID_ALPHA},
                "temporal": {"mode": config.TEMPORAL_MODE, "lambda": config.TEMPORAL_LAMBDA,
                             "hist": config.HIST_WEIGHT, "recent": config.RECENT_WEIGHT}}
    try:
        versions["preprocess"] = json.loads(
            (config.DATA_PROCESSED_DIR / "preprocess_report.json").read_text())
    except (FileNotFoundError, ValueError):
        pass
    (config.MODELS_DIR / "versions.json").write_text(json.dumps(versions, indent=2, default=str))
    print("Saved models/recommenders.joblib (baseline + adaptive) + versions.json.")


if __name__ == "__main__":
    main()
