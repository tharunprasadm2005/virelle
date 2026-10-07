"""TasteFlow home + taste APIs: personalized shelves, taste profile, evolution.

User-facing language only (no model jargon). All values from the real engine.
"""
from fastapi import APIRouter, Depends

from backend.app import db as appdb
from backend.app.api.cards import card
from backend.app.auth import current_user_id
from backend.app.deps import rmap as _rmap, rname as _rname
from src.recommender import taste as T
from src.recommender.explanations import explain

router = APIRouter(tags=["taste"])


def _cards(state, recs):
    rmap = state.get("rmap")
    if rmap is None:
        rmap = state["recipes"].set_index("recipe_id")
    out = []
    for r in recs:
        rid = int(r["recipe_id"])
        if rid not in rmap.index:
            continue
        c = card(rmap.loc[rid], rid)
        c["match_score"] = round(float(r["score"]), 3)
        out.append(c)
    return out


def _why(state, eff_uid, rec, meta, ctx=None):
    ua = state.get("ua")
    ra = state.get("ra")
    urow = None
    if ua is not None and len(ua) and eff_uid in set(ua["user_id"]):
        urow = ua[ua["user_id"] == eff_uid].iloc[0].to_dict()
    rrow = None
    if ra is not None and len(ra) and rec["recipe_id"] in set(ra["recipe_id"]):
        rrow = ra[ra["recipe_id"] == rec["recipe_id"]].iloc[0].to_dict()
    parts = {k: rec.get(k, 0.0) for k in ("baseline", "temporal", "aspect")}
    lines = explain(eff_uid, rec["recipe_id"], parts, meta, urow, rrow, state["recipes"])
    ctx = ctx or {}
    # product-signal lines — each gated on measured data, deterministic, no LLM
    if ctx.get("pantry_coverage") is not None and ctx["pantry_coverage"] >= 0.5:
        lines.append(f"You have {round(ctx['pantry_coverage']*100)}% of the ingredients in your pantry.")
    if ctx.get("missing_count") == 0 and ctx.get("pantry_size", 0) > 0:
        lines.append("You have everything needed to cook this right now.")
    elif isinstance(ctx.get("missing_count"), int) and ctx.get("missing_count", 99) <= 2 and ctx.get("pantry_size", 0) > 0:
        lines.append(f"You're missing only {ctx['missing_count']} ingredient(s) — one tap adds them to your list.")
    if ctx.get("nutrition_goal_hit"):
        lines.append(f"This matches your '{ctx['nutrition_goal_hit']}' preference.")
    if ctx.get("intent_hit"):
        lines.append("This matches what you're looking for right now.")
    if ctx.get("liked_similar"):
        lines.append(f"Similar to {ctx['liked_similar']}, which you enjoyed.")
    return lines


def _home_recs(state, uid, eff, adapt, base, prefs, k=10):
    """Personalized picks; onboarding-aware cold start via the engine's own
    new-user path (real user data, popularity only as fallback)."""
    from src.recommender.taste import onboarding_profile
    if eff is None:
        prof = onboarding_profile(prefs)
        recs = base.recommend_new_user(k=k, max_minutes=prefs.get("max_minutes"))
        return recs, {"stage": "getting_to_know", "message": "Getting to know your taste — based on your onboarding choices."}, prof
    recs, meta = adapt.recommend(eff, k=k, ablation="full")
    return recs, {"stage": "personalized", "message": "Your personalized recommendations are ready.",
                  "shift": meta["shift"]}, None


@router.get("/api/home")
def home(uid: int = Depends(current_user_id), intent: str | None = None):
    """Home feed. `intent` (e.g. '?intent=quick dinner') is SHORT-TERM session
    intent: it re-ranks this response only and never touches the stored taste
    profile or the research temporal model (Phase 14 separation)."""
    from backend.app.deps import STATE
    from src import config
    s = STATE
    if "adaptive" not in s:
        from fastapi import HTTPException
        from src import config
        raise HTTPException(503, config.MISSING_DATA_MSG)
    prefs = T.get_profile(uid)
    base, adapt, eff, has_activity = T.get_engine_for_app_user(s, uid)
    eff_or_none = eff if has_activity else None
    recs, info, _ = _home_recs(s, uid, eff_or_none, adapt, base, prefs, k=12)
    cards = _cards(s, recs)
    meta = {"shift": 0.0}
    if has_activity:
        _, meta = adapt.recommend(eff, k=1, ablation="full")
    # --- product layer: intent boost (session-only) + fatigue penalties + diversity
    rmap = _rmap(s)
    intent_toks = {t for t in (intent or "").lower().split() if len(t) > 2}
    shown_recent = {r["recipe_id"] for r in appdb.fetch_all(
        "SELECT DISTINCT recipe_id FROM recommendation_events WHERE user_id=? AND event_type='SHOWN'"
        " AND created_at > datetime('now','-3 days') LIMIT 60", (uid,))}
    opened = {r["recipe_id"] for r in appdb.fetch_all(
        "SELECT DISTINCT recipe_id FROM recommendation_events WHERE user_id=? AND event_type='OPENED'", (uid,))}
    cooked = {r["recipe_id"] for r in appdb.fetch_all(
        "SELECT DISTINCT recipe_id FROM user_recipe_interactions WHERE user_id=? AND interaction_type='COOKED'"
        " AND created_at > datetime('now','-14 days')", (uid,))}
    pantry = {r["normalized_name"].lower() for r in appdb.fetch_all(
        "SELECT normalized_name FROM pantry_items WHERE user_id=? AND available=1", (uid,))}
    import sqlite3
    namedb = config.DATA_PROCESSED_DIR / "recipe_ingredient_names.sqlite"
    names_of = {}
    if pantry and namedb.exists():
        conn = sqlite3.connect(str(namedb))
        try:
            ids = tuple(c["recipe_id"] for c in cards)
            if ids:
                q = f"SELECT recipe_id, name FROM recipe_names WHERE recipe_id IN ({','.join('?'*len(ids))})"
                for rid, nm in conn.execute(q, ids):
                    names_of.setdefault(rid, set()).add(nm)
        finally:
            conn.close()
    goals = set(prefs.get("nutrition_goals", []))
    rescored, tag_count = [], {}
    for c, r in zip(cards, recs):
        sc = c.get("match_score", 0)
        rid = c["recipe_id"]
        if rid in shown_recent and rid not in opened:
            sc -= config.FATIGUE_SHOWN_PENALTY
        if rid in cooked:
            sc -= config.FATIGUE_COOKED_PENALTY
        lead = (c.get("tags") or [""])[0]
        tag_count[lead] = tag_count.get(lead, 0) + 1
        if tag_count[lead] > config.FATIGUE_MAX_SAME_TAG:
            sc -= 0.05
        intent_hit = bool(intent_toks and intent_toks & set(f"{c['name']} {' '.join(c.get('tags', []))}".lower().split()))
        if intent_hit:
            sc += 0.1
        cov, miss_n = None, None
        if pantry and rid in names_of and names_of[rid]:
            cov = len(names_of[rid] & pantry) / len(names_of[rid])
            miss_n = len(names_of[rid] - pantry)
        ctx = {"pantry_coverage": cov, "missing_count": miss_n,
               "pantry_size": len(pantry), "intent_hit": intent_hit,
               "nutrition_goal_hit": "high protein" if ("high protein" in goals and c.get("nutrition_boosted")) else None,
               "liked_similar": None}
        c["why"] = _why(s, eff_or_none or 0, r, meta, ctx)
        rescored.append((sc, c))
    rescored.sort(key=lambda x: -x[0])
    cards = [c for _, c in rescored]
    # shelves from real data + engine
    import pandas as pd
    df = s["recipes"]
    disliked = {r["recipe_id"] for r in appdb.fetch_all(
        "SELECT recipe_id FROM user_recipe_interactions WHERE user_id=? AND interaction_type='DISLIKE'", (uid,))}
    def shelf(picks, n, label):
        if disliked:
            picks = picks[~picks["recipe_id"].isin(disliked)]
        # editorial preference: live photos first, unchecked next, audited-dead last.
        # Personalized ranking above is untouched by this.
        from backend.app.api.cards import image_ok
        order = picks.head(max(n * 4, 40)).copy()
        order["__img"] = [0 if image_ok(int(r)) is True else (2 if image_ok(int(r)) is False else 1)
                          for r in order["recipe_id"]]
        order = order.sort_values("__img", kind="stable")
        return {"label": label, "recipes": [card(r) for r in order.head(n).to_dict(orient="records")]}
    def maybe_pop(frame):
        if "ReviewCount" in frame.columns:
            return frame.sort_values("ReviewCount", ascending=False)
        return frame
    pop = maybe_pop(df)
    shelves = [shelf(pop, 10, "Popular right now")]
    if "minutes" in df.columns:
        shelves.append(shelf(maybe_pop(df[df["minutes"] <= 30]), 10, "Ready in 30 minutes or less"))
    if "tags_text" in df.columns:
        shelves.append(shelf(maybe_pop(df[df["tags_text"].str.contains("healthy", case=False, na=False)]), 10, "Healthy choices"))
    saved_rows = appdb.fetch_all("SELECT DISTINCT recipe_id FROM user_recipe_interactions WHERE user_id=? AND interaction_type='SAVE'", (uid,))
    saved_ids = [r["recipe_id"] for r in saved_rows]
    rmap = _rmap(s)
    saved = [card(rmap.loc[i], i) for i in saved_ids if i in rmap.index][:10]
    goals = set(prefs.get("nutrition_goals", []))
    if goals and cards:
        import pandas as pd
        prot = pd.to_numeric(rmap["ProteinContent"], errors="coerce") \
            if "ProteinContent" in rmap.columns else None
        cals = pd.to_numeric(rmap["Calories"], errors="coerce") \
            if "Calories" in rmap.columns else None
        scored = []
        for c in cards:
            b = 0.0
            rid = c["recipe_id"]
            if "high protein" in goals and prot is not None and rid in prot.index and prot[rid] == prot[rid]:
                b += min(1.0, float(prot[rid]) / 30.0) * 0.2
            if goals & {"lighter meals", "calorie aware"} and cals is not None and rid in cals.index and cals[rid] == cals[rid]:
                b += max(0.0, (800.0 - min(800.0, float(cals[rid]))) / 800.0) * 0.15
            scored.append((c.get("match_score", 0) + b, c))
        scored.sort(key=lambda x: -x[0])
        cards = [c for _, c in scored]
        for c in cards:
            c["nutrition_boosted"] = True
    return {"greeting_for": appdb.fetch_one("SELECT name FROM users WHERE id=?", (uid,))["name"],
            "stage": info, "recommended": cards, "shelves": shelves, "saved": saved,
            "nutrition_goals": sorted(goals)}


@router.get("/api/taste/evolution")
def taste_evolution(uid: int = Depends(current_user_id)):
    """Earlier vs recent recipe names for THIS app user (real data only)."""
    from backend.app.deps import STATE
    from src.recommender import temporal as TMP
    from src.recommender.temporal import split_old_recent
    s = STATE
    base, adapt, eff, has_activity = T.get_engine_for_app_user(s, uid)
    if not has_activity:
        return {"has_history": False}
    g = adapt.inter[adapt.inter["user_id"] == eff].sort_values("date")
    old, recent = split_old_recent(g)
    rmap = _rname(s)
    def names(frame, n=3):
        first = frame.sort_values("date").head(n)
        return [{"recipe_id": int(r), "name": str(rmap.get(r, f"Recipe {r}"))}
                for r in first["recipe_id"]]
    tp = TMP.user_temporal_profile(eff, adapt.inter, s["recipes"])
    return {"has_history": True, "shift": round(tp["shift"], 3),
            "earlier_recipes": names(old), "recent_recipes": names(recent)}


@router.get("/api/taste")
def taste(uid: int = Depends(current_user_id)):
    """My Taste: preference bars + evolution in plain language, all computed."""
    from backend.app.deps import STATE
    from src.recommender import temporal as TMP
    s = STATE
    prefs = T.get_profile(uid)
    base, adapt, eff, has_activity = T.get_engine_for_app_user(s, uid)
    if not has_activity:
        return {"has_history": False, "message": "Not enough activity yet — like or cook a few recipes first.",
                "onboarding": prefs}
    tp = TMP.user_temporal_profile(eff, adapt.inter, s["recipes"])
    # cuisine bars from this user's own rows
    import pandas as pd
    mine = adapt.inter[adapt.inter["user_id"] == eff]
    rmap = _rmap(s)
    from collections import Counter
    cats = Counter()
    for rid in mine["recipe_id"]:
        if rid in rmap.index:
            for t in str(rmap.loc[rid, "tags_text"]).split():
                cats[t] += 1
    top = [{"label": k, "count": v} for k, v in cats.most_common(12)]
    aspects = {}
    if len(s.get("ua", pd.DataFrame())) and eff in set(s["ua"]["user_id"]):
        row = s["ua"][s["ua"]["user_id"] == eff].iloc[0]
        aspects = {c: round(float(row[c]), 2) for c in s["ua"].columns if c != "user_id" and row[c] != 0}
    return {"has_history": True, "shift": round(tp["shift"], 3),
            "n_old": tp["n_old"], "n_recent": tp["n_recent"],
            "evolution_ready": tp["n_old"] >= 3 and tp["n_recent"] >= 3,
            "evolution_note": ("Not enough activity yet to identify a preference change."
                               if not (tp["n_old"] >= 3 and tp["n_recent"] >= 3) else None),
            "cuisines": top, "aspects": aspects, "onboarding": prefs}
