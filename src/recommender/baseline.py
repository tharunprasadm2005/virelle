"""Baseline recommender — preserves the original approach.

Pipeline: TF-IDF content similarity + matrix-factorisation CF, hybrid
alpha=0.7 CF / 0.3 CB (same as baseline_original), popularity fallback
for cold start. Exposes recommend_baseline(user_id, k=10).
"""
import numpy as np
import pandas as pd
from src import config
from src.data import features as F


class BaselineRecommender:
    def __init__(self, recipes, inter, tfidf_vec=None, tfidf_mat=None, cf_model=None):
        self.recipes = recipes.reset_index(drop=True)
        self.inter = inter
        self.vec = tfidf_vec
        self.tmat = tfidf_mat
        self.cf = cf_model
        self.by_id = self.recipes.set_index("recipe_id")
        pop = inter["recipe_id"].value_counts()
        self.recipes["n_ratings"] = self.recipes["recipe_id"].map(pop).fillna(0).astype(int)
        self.pop_map = self.recipes.set_index("recipe_id")["n_ratings"]
        self.user_items = {str(u): set(g["recipe_id"].tolist()) for u, g in inter.groupby("user_id")}
        self._cb_cache = {}

    def _cb(self, seeds, topn=200):
        key = (tuple(sorted(int(s) for s in seeds)), int(topn))
        if key not in self._cb_cache:
            self._cb_cache[key] = F.content_scores(seeds, self.recipes, self.tmat, topn=topn)
        return self._cb_cache[key]

    @classmethod
    def train(cls, recipes, inter, max_features=20000, n_components=50):
        vec, mat = F.build_tfidf(recipes, max_features)
        cf = F.build_cf(inter, n_components)
        return cls(recipes, inter, vec, mat, cf)

    def _seed_ids(self, user_id, n=3):
        u = self.inter[self.inter["user_id"] == user_id].sort_values("rating", ascending=False)
        return u.head(n)["recipe_id"].tolist()

    def recommend_baseline(self, user_id, k=10):
        rated = self.user_items.get(str(user_id), set())
        seeds = self._seed_ids(user_id)
        cb = self._cb(seeds, topn=200) if seeds else {}
        cands = [r for r in cb if r not in rated]
        if len(cands) < k:
            need = k - len(cands) + 20
            pop = [r for r in self.pop_map.sort_values(ascending=False).index
                   if r not in rated and r not in cands][:need]
            cands += pop
        scored = []
        for rid in cands:
            cf_s = F.cf_predict(self.cf, user_id, rid) if user_id in self.cf["uix"] else 2.5
            cb_s = 1.0 + cb.get(rid, 0.0) * 4.0
            score = config.HYBRID_ALPHA * cf_s + (1 - config.HYBRID_ALPHA) * cb_s
            scored.append((rid, score, cf_s, cb_s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [{"recipe_id": int(r), "score": float(s),
                 "cf_score": float(a), "cb_score": float(b)} for r, s, a, b in scored[:k]]

    def recommend_new_user(self, k=10, cuisine=None, max_minutes=None):
        df = self.recipes
        if max_minutes is not None and "minutes" in df.columns:
            df = df[df["minutes"] <= max_minutes]
        if cuisine and "tags_text" in df.columns:
            m = df["tags_text"].str.contains(cuisine.lower(), na=False)
            if m.any():
                df = df[m]
        df = df.sort_values("n_ratings", ascending=False).head(k)
        return [{"recipe_id": int(r.recipe_id), "score": float(r.n_ratings),
                 "cf_score": 0.0, "cb_score": 0.0} for r in df.itertuples()]


def recommend_baseline(user_id, k=10, _state=None):
    """Functional interface required by spec: recommend_baseline(user_id, k=10)."""
    if _state is None:
        raise RuntimeError("Recommender state not loaded — call backend startup or train pipeline first.")
    return _state["baseline"].recommend_baseline(user_id, k=k)
