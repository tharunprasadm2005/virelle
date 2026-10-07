"""Final hybrid: w1*baseline + w2*temporal + w3*aspect (configurable, validated)."""
import numpy as np
from src import config
from src.data import features as F
from src.recommender import temporal as T
from src.recommender.aspect_model import aspect_compatibility


class AdaptiveRecommender:
    def __init__(self, baseline, recipes, inter, user_aspects, recipe_aspects,
                 w_b=None, w_t=None, w_a=None):
        config.validate_weights()
        self.b = baseline
        self.recipes = recipes
        self.inter = inter
        self.ua = user_aspects.set_index("user_id") if len(user_aspects) else None
        self.ra = recipe_aspects.set_index("recipe_id") if len(recipe_aspects) else None
        self.w_b = config.W_BASELINE if w_b is None else w_b
        self.w_t = config.W_TEMPORAL if w_t is None else w_t
        self.w_a = config.W_ASPECT if w_a is None else w_a
        self.aspect_cols = [c for c in (user_aspects.columns if len(user_aspects) else []) if c != "user_id"]
        self._tprof_cache = {}
        self._base_cache = {}
        self._content_by_id = dict(zip(recipes["recipe_id"].astype(int),
                                       recipes["content_features"].fillna("").astype("object")))

    def _tprof(self, user_id):
        if user_id not in self._tprof_cache:
            self._tprof_cache[user_id] = T.user_temporal_profile(user_id, self.inter, self.recipes)
        return self._tprof_cache[user_id]

    def _norm(self, scores):
        vals = np.array([s for _, s in scores], float)
        if vals.size == 0:
            return scores
        lo, hi = vals.min(), vals.max()
        if hi - lo < 1e-9:
            return [(r, 0.5) for r, _ in scores]
        return [(r, float((s - lo) / (hi - lo))) for r, s in scores]

    def recommend(self, user_id, k=10, ablation="full"):
        rated = self.b.user_items.get(str(user_id), set())
        n_base = max(k * 5, 50)
        if (user_id, n_base) not in self._base_cache:
            self._base_cache[(user_id, n_base)] = self.b.recommend_baseline(user_id, k=n_base)
        base = self._base_cache[(user_id, n_base)]
        cand_ids = [r["recipe_id"] for r in base]
        base_map = {r["recipe_id"]: r["score"] for r in base}
        bn = dict(self._norm([(r, base_map[r]) for r in cand_ids]))
        # temporal
        tp = self._tprof(user_id)
        tb = T.temporal_boost(cand_ids, self._content_by_id, tp["recent_pref_text"]) if ablation in ("full", "temporal") else {r: 0.0 for r in cand_ids}
        tn = dict(self._norm(list(tb.items())))
        # aspect
        an = {}
        if ablation in ("full", "aspect") and self.ua is not None and user_id in self.ua.index:
            uv = self.ua.loc[user_id, self.aspect_cols].to_numpy(float)
            for r in cand_ids:
                if self.ra is not None and r in self.ra.index:
                    an[r] = aspect_compatibility(uv, self.ra.loc[r, self.aspect_cols].to_numpy(float))
                else:
                    an[r] = 0.0
            an = dict(self._norm(list(an.items())))
        else:
            an = {r: 0.0 for r in cand_ids}
        use_t = ablation in ("full", "temporal")
        use_a = ablation in ("full", "aspect")
        wb, wt, wa = self.w_b, (self.w_t if use_t else 0.0), (self.w_a if use_a else 0.0)
        tot = wb + wt + wa or 1.0
        wb, wt, wa = wb / tot, wt / tot, wa / tot
        if ablation == "baseline":
            wb, wt, wa = 1.0, 0.0, 0.0
        final = []
        for r in cand_ids:
            if r in rated:
                continue
            s = wb * bn.get(r, 0) + wt * tn.get(r, 0) + wa * an.get(r, 0)
            final.append({"recipe_id": r, "score": float(s),
                          "baseline": float(bn.get(r, 0)), "temporal": float(tn.get(r, 0)),
                          "aspect": float(an.get(r, 0))})
        final.sort(key=lambda x: x["score"], reverse=True)
        return final[:k], {"shift": tp["shift"], "n_old": tp["n_old"], "n_recent": tp["n_recent"],
                           "weights": {"w_b": wb, "w_t": wt, "w_a": wa}}
