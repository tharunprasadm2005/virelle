import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Ablation on REAL data: baseline | +temporal | +aspect | full. Saves CSVs + figures."""
import sys
import joblib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from src import config
from src.recommender.baseline import BaselineRecommender
from src.recommender.hybrid import AdaptiveRecommender
from src.recommender.evaluate import temporal_split, evaluate_model


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-users", type=int, default=3000,
                    help="Cap test users (seeded sample) for full-scale runtime; use all when <=0.")
    args = ap.parse_args()
    try:
        recipes = pd.read_csv(config.DATA_PROCESSED_DIR / "recipes_processed.csv")
        inter = pd.read_csv(config.DATA_PROCESSED_DIR / "interactions_processed.csv")
        ua = pd.read_csv(config.DATA_PROCESSED_DIR / "user_aspects.csv")
        ra = pd.read_csv(config.DATA_PROCESSED_DIR / "recipe_aspects.csv")
    except FileNotFoundError:
        print("ERROR: pipeline outputs missing — run preprocess -> build_features -> train first (real data required).")
        sys.exit(2)
    inter["date"] = pd.to_datetime(inter["date"], errors="coerce")
    train, test = temporal_split(inter)
    print(f"Temporal split: train={len(train)}, test(liked recent)={len(test)}")
    if len(test) == 0:
        print("ERROR: no recent liked interactions for testing — dataset too small/filtered.")
        sys.exit(2)
    test_by_user = test.groupby("user_id")["recipe_id"].apply(list).to_dict()
    if args.max_users and args.max_users > 0 and len(test_by_user) > args.max_users:
        rng = np.random.RandomState(config.RANDOM_STATE)
        keep = set(rng.choice(sorted(test_by_user), size=args.max_users, replace=False).tolist())
        test_by_user = {u: v for u, v in test_by_user.items() if u in keep}
        print(f"Sampled {len(test_by_user)} test users (seed={config.RANDOM_STATE}).")
    # retrain on TRAIN only (no leakage), reuse pipeline pieces
    from src.data import features as F
    vec, mat = F.build_tfidf(recipes)
    cf = F.build_cf(train)
    base = BaselineRecommender(recipes, train, vec, mat, cf)
    from src.recommender import aspect_model as A
    tua, tra = A.build_aspect_tables(train)
    adapt = AdaptiveRecommender(base, recipes, train, tua, tra)
    modes = ["baseline", "temporal", "aspect", "full"]
    fns = {"baseline": lambda u, k: adapt.recommend(u, k=k, ablation="baseline")[0],
           "temporal": lambda u, k: adapt.recommend(u, k=k, ablation="temporal")[0],
           "aspect": lambda u, k: adapt.recommend(u, k=k, ablation="aspect")[0],
           "full": lambda u, k: adapt.recommend(u, k=k, ablation="full")[0]}
    all_rows = []
    for m in modes:
        rows = evaluate_model(fns[m], test_by_user, k_list=(5, 10))
        for r in rows:
            all_rows.append({"model": m, **r})
        print(m, rows)
    out = pd.DataFrame(all_rows)
    config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(config.EXPERIMENTS_DIR / "ablation_results.csv", index=False)
    # figures
    config.REPORTS_FIG_DIR.mkdir(parents=True, exist_ok=True)
    for metric in ["P", "R", "NDCG"]:
        piv = out[out["K"] == 10].set_index("model")[f"{metric}@10"].reindex(modes)
        plt.figure()
        piv.plot(kind="bar")
        plt.title(f"{metric}@10 by model (real Food.com data)")
        plt.tight_layout()
        plt.savefig(config.REPORTS_FIG_DIR / f"{metric.lower()}_at_10.png")
        plt.close()
    print("Wrote experiments/ablation_results.csv + reports/figures/")


if __name__ == "__main__":
    main()
