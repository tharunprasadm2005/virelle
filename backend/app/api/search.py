"""Recipe search + discovery over REAL Food.com data, personalized re-ranking.

Search relevance (TF-IDF cosine on the same content matrix the engine uses)
+ personal preference signals. The hybrid recommender itself is untouched.
"""
from fastapi import APIRouter, Depends, Query
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

from backend.app import db as appdb
from backend.app.api.cards import card
from backend.app.auth import current_user_id
from src.recommender import taste as T

router = APIRouter(tags=["search"])


@router.get("/api/recipes/search")
def search(q: str = Query(min_length=1, max_length=200), limit: int = Query(24, ge=1, le=60),
           max_minutes: int | None = None, diet: str | None = None,
           mode: str = Query("hybrid", pattern="^(keyword|hybrid)$"),
           min_protein: float | None = None, max_calories: float | None = None,
           uid: int = Depends(current_user_id)):
    """Product search. mode=keyword: TF-IDF + cuisine boost (legacy behavior).
    mode=hybrid (default): keyword + semantic + preference fusion with weights
    from src/config.py (SEARCH_W_*). Research pipeline untouched by these."""
    from backend.app.deps import STATE
    from src import config
    s = STATE
    vec = s["baseline"].vec
    tmat = s["baseline"].tmat
    df = s["recipes"]
    qv = vec.transform([q])
    sims = cosine_similarity(qv, tmat).ravel()
    idx = sims.argsort()[::-1][:400]
    picks = df.iloc[idx].copy()
    picks["rel"] = sims[idx]
    picks = picks[picks["rel"] > 0]
    kw = {int(r): float(v) for r, v in zip(picks["recipe_id"], picks["rel"])}
    sem_map: dict[int, float] = {}
    if mode == "hybrid":
        from src.recommender import semantic_search as _sem
        if _sem.available():
            try:
                ids, scores = _sem.search(q, k=400)
                sem_map = dict(zip(ids, scores))
            except Exception:
                sem_map = {}
    union_ids = list(dict.fromkeys(list(kw) + list(sem_map)))
    import numpy as np

    def _norm(m):
        if not m:
            return {}
        vals = np.array(list(m.values()), float)
        lo, hi = vals.min(), vals.max()
        if hi - lo < 1e-9:
            return {k: 0.5 for k in m}
        return {k: float((v - lo) / (hi - lo)) for k, v in m.items()}
    kwn, smn = _norm(kw), _norm(sem_map)
    # preference: cuisine/tag overlap + aspect compatibility (existing signals)
    prefs = T.get_profile(uid)
    pref_map: dict[int, float] = {}
    if prefs.get("cuisines"):
        from backend.app.deps import rmap as _rmap
        rmap = _rmap(s)
        for rid in union_ids:
            if rid in rmap.index:
                tags = str(rmap.loc[rid, "tags_text"]) if "tags_text" in df.columns else ""
                pref_map[rid] = sum(0.5 for c in prefs["cuisines"] if c.lower() in tags.lower())
    ua = s.get("ua")
    base, adapt, eff, has_activity = T.get_engine_for_app_user(s, uid)
    if ua is not None and len(ua) and eff in set(ua["user_id"]):
        from src.recommender.aspect_model import aspect_compatibility
        acols = [cc for cc in ua.columns if cc != "user_id"]
        uv = ua[ua["user_id"] == eff].iloc[0][acols].to_numpy(float)
        ra = s.get("ra")
        if ra is not None and len(ra):
            rsub = ra[ra["recipe_id"].isin(union_ids)]
            for row in rsub.itertuples():
                pref_map[row.recipe_id] = pref_map.get(row.recipe_id, 0.0) + max(
                    0.0, aspect_compatibility(uv, np.array([getattr(row, cc) for cc in acols], float)))
    prn = _norm(pref_map)
    scored_ids = [(rid, config.SEARCH_W_KEYWORD * kwn.get(rid, 0.0) +
                   config.SEARCH_W_SEMANTIC * smn.get(rid, 0.0) +
                   config.SEARCH_W_PREF * prn.get(rid, 0.0)) for rid in union_ids]
    order = {rid: sc for rid, sc in scored_ids}
    picks = df[df["recipe_id"].isin(order)].copy()
    picks["score"] = picks["recipe_id"].map(order)
    if min_protein is not None and "ProteinContent" in picks.columns:
        picks = picks[pd.to_numeric(picks["ProteinContent"], errors="coerce").fillna(0) >= min_protein]
    if max_calories is not None and "Calories" in picks.columns:
        picks = picks[pd.to_numeric(picks["Calories"], errors="coerce").fillna(10 ** 9) <= max_calories]
    if max_minutes and "minutes" in picks.columns:
        picks = picks[picks["minutes"] <= max_minutes]
    if diet and diet.strip().lower() in ("vegetarian", "vegan"):
        # knowledge-based dietary filtering (replaces the old regex approach)
        from src.ingredients import knowledge as K
        from backend.app.api.cards import _lst as _lst_fn
        want = diet.strip().lower() + "_ok"  # vegetarian_ok | vegan_ok
        keep = []
        for _, row in picks.iterrows():
            raw = _lst_fn(row["ingredients"]) if "ingredients" in picks.columns else []
            keep.append(all(K.diet_flags_for_raw(i).get(want, True) for i in raw) if raw else True)
        picks = picks[keep]
    # personalization: boost preferred cuisines/tags + recent taste, exclude dislikes
    disliked = {r["recipe_id"] for r in appdb.fetch_all(
        "SELECT recipe_id FROM user_recipe_interactions WHERE user_id=? AND interaction_type='DISLIKE'", (uid,))}
    if disliked:
        picks = picks[~picks["recipe_id"].isin(disliked)]
    picks = picks.sort_values("score", ascending=False).head(limit)
    return {"query": q, "mode": mode, "results": [card(r) for r in picks.to_dict(orient="records")],
            "weights": {"keyword": config.SEARCH_W_KEYWORD, "semantic": config.SEARCH_W_SEMANTIC,
                        "pref": config.SEARCH_W_PREF}}


@router.get("/api/recipes/semantic-search")
def semantic_search(q: str = Query(min_length=1, max_length=200),
                    limit: int = Query(24, ge=1, le=60), uid: int = Depends(current_user_id)):
    """Pure semantic candidates (MiniLM+FAISS). Personalized fusion lives in
    /api/recipes/search?mode=hybrid (Phase 7); this endpoint exposes the sidecar."""
    from backend.app.deps import STATE
    from src.recommender import semantic_search as sem
    from backend.app.api.cards import card
    if not sem.available():
        from fastapi import HTTPException
        raise HTTPException(503, "Semantic index not built — run scripts/build_semantic_index.py")
    ids, scores = sem.search(q, k=max(limit * 4, 100))
    from backend.app.deps import rmap as _rmap
    rmap = _rmap(STATE)
    out = []
    for rid, sc in zip(ids, scores):
        if rid in rmap.index:
            c = card(rmap.loc[rid], rid)
            c["semantic_score"] = round(sc, 3)
            out.append(c)
        if len(out) >= limit:
            break
    return {"query": q, "results": out}


@router.get("/api/discover")
def discover(uid: int = Depends(current_user_id)):
    from backend.app.deps import STATE
    df = STATE["recipes"]
    pop = df.sort_values("ReviewCount", ascending=False) if "ReviewCount" in df.columns else df
    def sec(mask, label, n=12):
        sub = df[mask].sort_values("ReviewCount", ascending=False).head(n) if "ReviewCount" in df.columns else df[mask].head(n)
        recs = [card(r) for r in sub.to_dict(orient="records")]
        return {"label": label, "recipes": recs} if recs else None
    tx = df["tags_text"].str.lower() if "tags_text" in df.columns else ""
    ix = df["ingredients_text"].str.lower() if "ingredients_text" in df.columns else ""
    return {"sections": [
        {"label": "Trending", "recipes": [card(r) for r in pop.head(12).to_dict(orient="records")]},
        sec(tx.str.contains("indian", na=False), "Indian"),
        sec(tx.str.contains("vegetarian|vegan|veggie|meatless", na=False), "Vegetarian"),
        sec(tx.str.contains("dessert|cake|cookie", na=False), "Desserts"),
        sec(df["minutes"] <= 30, "Quick (≤30 min)") if "minutes" in df.columns else None,
        sec(tx.str.contains("healthy|low fat", na=False), "Healthy"),
        sec(ix.str.contains("chicken", na=False), "Chicken"),
    ]}
