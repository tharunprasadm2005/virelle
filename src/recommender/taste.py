"""Personalization bridge: Virelle app activity -> existing AI engine.

No model logic lives here. This module only:
1. loads precomputed artifacts (once, via STATE),
2. maps an app user to ONE effective recommendation id
   (linked Food.com history, else an app-namespace id that never collides),
3. appends the app user's GENUINE interactions (likes/ratings/reviews with now()
   timestamps, so recency works) to the historical frame the engine expects,
4. calls the untouched Baseline/Adaptive recommenders + explanations.

Historical Food.com rows and app rows are never mixed up: app rows are tagged
in `source` and only ever attached to their own user's effective id.
"""
import pandas as pd

APP_UID_BASE = 50_000_000

# app interaction -> implicit rating for the engine (likes/dislikes strength)
TYPE_RATING = {"LIKE": 5, "COOKED": 4, "SAVE": 4, "RATED": None, "DISLIKE": 2, "REVIEW": 4}


def get_profile(user_id: int):
    from backend.app import db as appdb
    import json
    row = appdb.fetch_one("SELECT * FROM user_preferences WHERE user_id=?", (user_id,))
    if row is None:
        return {"diet": "", "cuisines": [], "priorities": [], "avoid_ingredients": [],
                "max_minutes": None, "nutrition_goals": []}
    cols = set(row.keys())
    return {"diet": row["diet"] or "",
            "cuisines": json.loads(row["cuisines"] or "[]"),
            "priorities": json.loads(row["priorities"] or "[]"),
            "avoid_ingredients": json.loads(row["avoid_ingredients"] or "[]"),
            "max_minutes": row["max_minutes"],
            "nutrition_goals": json.loads(row["nutrition_goals"] or "[]") if "nutrition_goals" in cols else []}


def effective_uid(app_user_id: int) -> int:
    from backend.app import db as appdb
    row = appdb.fetch_one("SELECT linked_foodcom_id FROM users WHERE id=?", (app_user_id,))
    if row and row["linked_foodcom_id"]:
        return int(row["linked_foodcom_id"])
    return APP_UID_BASE + int(app_user_id)


def app_interaction_rows(app_user_id: int, eff_uid: int) -> pd.DataFrame:
    from backend.app import db as appdb
    rows = appdb.fetch_all(
        "SELECT recipe_id, interaction_type, rating, review_text, created_at "
        "FROM user_recipe_interactions WHERE user_id=? ORDER BY created_at", (app_user_id,))
    recs = []
    for r in rows:
        if r["interaction_type"] in ("UNSAVE",):
            continue
        rating = r["rating"] if r["rating"] else TYPE_RATING.get(r["interaction_type"])
        if rating is None:
            continue
        recs.append({"user_id": eff_uid, "recipe_id": int(r["recipe_id"]), "rating": int(rating),
                     "review": r["review_text"] or "", "date": r["created_at"], "source": "app"})
    if not recs:
        return pd.DataFrame(columns=["user_id", "recipe_id", "rating", "review", "date", "source"])
    out = pd.DataFrame(recs)
    out["date"] = pd.to_datetime(out["date"], errors="coerce").fillna(pd.Timestamp.now())
    return out


_EPHEMERAL = {}


def get_engine_for_app_user(state, app_user_id: int):
    """Ephemeral (base, adaptive) pair that sees exactly this app user's rows:
    their linked Food.com history (if any) + their genuine app interactions.
    Shares all heavy artifacts (TF-IDF, SVD, aspects, popularity); no model
    logic is altered — only which rows the instances observe.
    Cached per user, invalidated when their interaction count changes.
    """
    import copy
    from backend.app import db as appdb
    eff = effective_uid(app_user_id)
    n = appdb.fetch_one("SELECT COUNT(*) c FROM user_recipe_interactions WHERE user_id=?",
                        (app_user_id,))["c"]
    key = (app_user_id, eff, n)
    if key in _EPHEMERAL:
        base, adapt, has_activity = _EPHEMERAL[key]
        return base, adapt, eff, has_activity
    hist = state["inter"]
    mine = app_interaction_rows(app_user_id, eff)
    known = state.get("known_uids")
    has_hist = (eff in known) if known is not None else eff in set(hist["user_id"].unique())
    own_hist = hist[hist["user_id"] == eff] if has_hist else hist.iloc[0:0]
    small = pd.concat([own_hist, mine], ignore_index=True) if len(mine) else own_hist
    small["date"] = pd.to_datetime(small["date"], errors="coerce")
    has_activity = len(small) > 0
    sb, sa = state["baseline"], state["adaptive"]
    base = copy.copy(sb)
    base.inter = small
    items = dict(sb.user_items)
    if len(small):
        items[str(eff)] = set(small["recipe_id"].astype(int).tolist())
    base.user_items = items
    adapt = copy.copy(sa)
    adapt.b = base
    adapt.inter = small if len(small) else hist
    adapt._tprof_cache = {}
    adapt._base_cache = {}
    _EPHEMERAL[key] = (base, adapt, has_activity)
    if len(_EPHEMERAL) > 8:  # bound memory: drop oldest entry
        _EPHEMERAL.pop(next(iter(_EPHEMERAL)))
    return base, adapt, eff, has_activity


def onboarding_profile(prefs: dict) -> dict:
    """Map onboarding answers onto the baseline new-user profile (real user data)."""
    diet = (prefs.get("diet") or "").lower()
    return {"username": "app_user",
            "dietary_preferences": {"vegetarian": diet in ("vegetarian", "vegan"),
                                    "vegan": diet == "vegan"},
            "preferred_cuisines": [c.lower() for c in prefs.get("cuisines", [])],
            "favorite_ingredients": [],
            "max_cook_time": prefs.get("max_minutes")}
