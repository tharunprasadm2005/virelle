"""What-can-I-cook: pantry coverage + personalization + quality, diet/time aware."""
import sqlite3
import numpy as np
from fastapi import APIRouter, Depends, Query

from src import config
from backend.app import db as appdb
from backend.app.api.cards import card
from backend.app.auth import current_user_id
from src.recommender import taste as T
from src.ingredients import knowledge as K

router = APIRouter(tags=["cook"])
_NAME_DB = None


def _db():
    global _NAME_DB
    if _NAME_DB is None:
        _NAME_DB = config.DATA_PROCESSED_DIR / "recipe_ingredient_names.sqlite"
    return _NAME_DB


def _pantry_names(uid):
    rows = appdb.fetch_all("SELECT normalized_name, label FROM pantry_items WHERE user_id=? AND available=1", (uid,))
    out = set()
    for r in rows:
        n = (r["normalized_name"] or "").strip().lower() or r["label"].strip().lower()
        if n:
            out.add(n)
    return out


@router.get("/api/cook/matches")
def matches(min_coverage: float = Query(0.3, ge=0.0, le=1.0), limit: int = Query(24, ge=1, le=60),
            diet: str | None = None, uid: int = Depends(current_user_id)):
    """Rank recipes by pantry coverage blended with personalization + quality.

    Score = COOK_W_COVERAGE*coverage + COOK_W_PREF*pref + COOK_W_QUALITY*quality.
    pref = content similarity to user's liked recipes + aspect compatibility (existing
    engine pieces, reused — engine logic itself untouched).
    """
    from backend.app.deps import STATE
    s = STATE
    pantry = _pantry_names(uid)
    if not pantry:
        return {"pantry_empty": True, "matches": [],
                "message": "Add a few ingredients and we'll find recipes you can make."}
    prefs = T.get_profile(uid)
    max_minutes = prefs.get("max_minutes")
    conn = sqlite3.connect(str(_db()))
    try:
        ph = ",".join("?" * len(pantry))
        names = tuple(sorted(pantry))
        # one indexed query: matched + total per candidate (no full-table GROUP BY);
        # HAVING hit>=2 + LIMIT bound the work no matter how common the pantry names are
        rows = conn.execute(
            f"""SELECT recipe_id, COUNT(*) AS tot, SUM(name IN ({ph})) AS hit
                FROM recipe_names
                WHERE recipe_id IN (SELECT recipe_id FROM recipe_names WHERE name IN ({ph}))
                GROUP BY recipe_id HAVING (hit >= 2 OR tot <= 4)
                ORDER BY hit DESC LIMIT 20000""",
            names + names).fetchall()
    finally:
        conn.close()
    cands = []
    for rid, tot, hit in rows:
        if not tot:
            continue
        cov = hit / tot
        if cov >= min_coverage:
            cands.append([rid, cov])
    cands.sort(key=lambda x: -x[1])
    cands = cands[:4000]
    if not cands:
        return {"pantry_empty": False, "matches": [], "pantry_size": len(pantry),
                "understood_as": sorted(pantry),
                "message": "No recipes reach 30% coverage with these ingredients. Check spelling or add staples like rice, onion, tomato."}
    # personalization: CB similarity to liked recipes + aspect compat
    base, adapt, eff, has_activity = T.get_engine_for_app_user(s, uid)
    pref_map, liked = {}, []
    if has_activity:
        liked = [int(r) for r in adapt.inter[(adapt.inter["user_id"] == eff) & (adapt.inter["rating"] >= 4)]["recipe_id"].tolist()]
    if liked:
        cb = base._cb(liked, topn=5000)
        mx = max(cb.values()) if cb else 1.0
        pref_map = {r: v / mx for r, v in cb.items()}
    avec = None
    ua = s.get("ua")
    if ua is not None and len(ua) and eff in set(ua["user_id"]):
        from src.recommender.aspect_model import aspect_compatibility
        acols = [cc for cc in ua.columns if cc != "user_id"]
        avec = ua[ua["user_id"] == eff].iloc[0][acols].to_numpy(float)
        ra = s.get("ra")
        if ra is not None and len(ra):
            rsub = ra[ra["recipe_id"].isin([c[0] for c in cands])]
            for row in rsub.itertuples():
                pref_map[row.recipe_id] = pref_map.get(row.recipe_id, 0.0) + 0.5 * max(
                    0.0, aspect_compatibility(avec, np.array([getattr(row, cc) for cc in acols], float)))
    rmap = s.get("rmap")
    if rmap is None:
        rmap = s["recipes"].set_index("recipe_id")
    disliked = {r["recipe_id"] for r in appdb.fetch_all(
        "SELECT recipe_id FROM user_recipe_interactions WHERE user_id=? AND interaction_type='DISLIKE'", (uid,))}
    avoid = [a.lower() for a in prefs.get("avoid_ingredients", [])]
    out = []
    for rid, cov in cands:
        if rid in disliked or rid not in rmap.index:
            continue
        row = rmap.loc[rid]
        if max_minutes and row["minutes"] > max_minutes:
            continue
        if diet and diet.strip().lower() in ("vegetarian", "vegan"):
            want = diet.strip().lower() + "_ok"
            if not all(K.diet_flags_for_raw(t).get(want, True) for t in
                       ([row["ingredients"]] if isinstance(row["ingredients"], str) else [])):
                continue
        if avoid and any(a in str(row.get("ingredients_text", "")) for a in avoid):
            continue
        try:
            n_rev = float(row.get("ReviewCount", 0))
            n_rat = float(row.get("AggregatedRating", 0))
        except (TypeError, ValueError):
            n_rev, n_rat = 0.0, 0.0
        qual = min(1.0, n_rev / 50.0) * 0.5 + min(5.0, max(0.0, n_rat)) / 5.0 * 0.5
        score = config.COOK_W_COVERAGE * cov + config.COOK_W_PREF * pref_map.get(rid, 0.0) + \
            config.COOK_W_QUALITY * (qual if qual == qual else 0.0)
        out.append((score, cov, rid))
    out.sort(reverse=True)
    res = []
    for score, cov, rid in out[:limit]:
        cc = card(rmap.loc[rid], rid)
        cc["coverage"] = round(cov, 2)
        cc["cook_score"] = round(score, 3)
        res.append(cc)
    return {"pantry_empty": False, "pantry_size": len(pantry), "matches": res,
            "weights": {"coverage": config.COOK_W_COVERAGE, "pref": config.COOK_W_PREF,
                        "quality": config.COOK_W_QUALITY}}


def _names_of(rid):
    conn = sqlite3.connect(str(_db()))
    try:
        return [r[0] for r in conn.execute("SELECT name FROM recipe_names WHERE recipe_id=?", (rid,))]
    finally:
        conn.close()


@router.get("/api/cook/missing/{recipe_id}")
def missing(recipe_id: int, uid: int = Depends(current_user_id)):
    pantry = _pantry_names(uid)
    names = set(_names_of(recipe_id))
    miss = sorted(n for n in names if n not in pantry)
    return {"recipe_id": recipe_id, "coverage": round(1 - len(miss) / len(names), 2) if names else 0.0,
            "missing": miss}


@router.post("/api/cook/missing-to-shopping/{recipe_id}")
def missing_to_shopping(recipe_id: int, uid: int = Depends(current_user_id)):
    from backend.app.api.shopping import categorize, _pantry_stock
    m = missing(recipe_id, uid)
    existing = {r["label"].lower() for r in appdb.fetch_all(
        "SELECT label FROM shopping_items WHERE user_id=? AND checked=0", (uid,))}
    stock = _pantry_stock(uid)
    added = 0
    for nm in m["missing"]:
        if nm[:120].lower() not in existing and nm[:120].lower() not in stock:
            appdb.execute("INSERT INTO shopping_items (user_id, label, category, recipe_id) VALUES (?,?,?,?)",
                          (uid, nm[:120], categorize(nm), recipe_id))
            existing.add(nm[:120].lower())
            added += 1
    return {"added": added, "missing": m["missing"]}
