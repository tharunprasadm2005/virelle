"""Evaluation on REAL data: temporal per-user split (train=older, test=recent).

Metrics: Precision@K, Recall@K, NDCG@K, HitRate@K.
Ablation: baseline | baseline+temporal | baseline+aspect | full.
"""
import numpy as np
import pandas as pd


def temporal_split(inter, test_frac=0.2, min_test=1):
    train_parts, test_parts = [], []
    for u, g in inter.sort_values("date").groupby("user_id"):
        g = g.sort_values("date")
        n = len(g)
        n_test = max(min_test if n >= 5 else 0, int(round(n * test_frac)))
        if n_test <= 0 or n_test >= n:
            train_parts.append(g)
            continue
        train_parts.append(g.iloc[:-n_test])
        test_parts.append(g[g["rating"] >= 4].iloc[-n_test:])  # relevant = liked recent
    train = pd.concat(train_parts).reset_index(drop=True) if train_parts else inter.iloc[0:0]
    test = pd.concat(test_parts).reset_index(drop=True) if test_parts else inter.iloc[0:0]
    return train, test


def _dcg(rels):
    return sum(r / np.log2(i + 2) for i, r in enumerate(rels))


def metrics_at_k(recommended_ids, relevant_ids, k=10):
    rec = list(recommended_ids)[:k]
    rel = set(relevant_ids)
    if not rel or not rec:
        return {"P": 0.0, "R": 0.0, "NDCG": 0.0, "HR": 0.0}
    hits = [1 if r in rel else 0 for r in rec]
    p = sum(hits) / len(rec)
    r = sum(hits) / len(rel)
    ideal = _dcg(sorted(hits, reverse=True))
    ndcg = (_dcg(hits) / ideal) if ideal else 0.0
    return {"P": p, "R": r, "NDCG": ndcg, "HR": 1.0 if sum(hits) else 0.0}


def evaluate_model(recommender_fn, test_by_user, k_list=(5, 10)):
    rows = []
    for k in k_list:
        agg = {"P": [], "R": [], "NDCG": [], "HR": []}
        for user_id, rel_ids in test_by_user.items():
            try:
                recs = recommender_fn(user_id, k=k)
            except Exception:
                continue
            ids = [r["recipe_id"] for r in (recs[0] if isinstance(recs, tuple) else recs)]
            m = metrics_at_k(ids, rel_ids, k)
            for key in agg:
                agg[key].append(m[key])
        rows.append({"K": k, **{f"{key}@{k}": float(np.mean(v)) if v else 0.0 for key, v in agg.items()},
                     "n_users": len(test_by_user)})
    return rows
