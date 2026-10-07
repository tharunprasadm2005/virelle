"""Weekly meal planner: CRUD + engine-powered week generation."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app import db as appdb
from backend.app.api.cards import card
from backend.app.auth import current_user_id
from src.recommender import taste as T

router = APIRouter(tags=["meals"])
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
SLOTS = ["breakfast", "lunch", "dinner"]


class SlotIn(BaseModel):
    day: str
    slot: str
    recipe_id: int | None = None


def _plan(uid, week_start):
    return appdb.fetch_one("SELECT * FROM meal_plans WHERE user_id=? AND week_start=?", (uid, week_start))


def _dump(plan_id):
    from backend.app.deps import STATE, rmap as _rmap
    rmap = _rmap(STATE)
    items = appdb.fetch_all("SELECT day, slot, recipe_id FROM meal_plan_items WHERE plan_id=?", (plan_id,))
    grid = {d: {s: None for s in SLOTS} for d in DAYS}
    for it in items:
        rid = it["recipe_id"]
        grid[it["day"]][it["slot"]] = card(rmap.loc[rid], rid) if rid and rid in rmap.index else None
    return grid


@router.get("/api/meal-plans")
def get_plan(week_start: str, uid: int = Depends(current_user_id)):
    p = _plan(uid, week_start)
    if not p:
        return {"week_start": week_start, "grid": {d: {s: None for s in SLOTS} for d in DAYS}}
    return {"week_start": week_start, "grid": _dump(p["id"])}


@router.put("/api/meal-plans/slot")
def set_slot(week_start: str, body: SlotIn, uid: int = Depends(current_user_id)):
    from backend.app.deps import STATE, recipe_ids as _ids
    if body.day not in DAYS or body.slot not in SLOTS:
        raise HTTPException(422, "Invalid day or slot")
    if body.recipe_id is not None and body.recipe_id not in _ids(STATE):
        raise HTTPException(404, "Unknown recipe")
    p = _plan(uid, week_start)
    pid = p["id"] if p else appdb.execute("INSERT INTO meal_plans (user_id, week_start) VALUES (?,?)", (uid, week_start))
    if body.recipe_id is None:
        appdb.execute("DELETE FROM meal_plan_items WHERE plan_id=? AND day=? AND slot=?", (pid, body.day, body.slot))
    else:
        appdb.execute("INSERT INTO meal_plan_items (plan_id, day, slot, recipe_id) VALUES (?,?,?,?)"
                      " ON CONFLICT(plan_id, day, slot) DO UPDATE SET recipe_id=excluded.recipe_id",
                      (pid, body.day, body.slot, body.recipe_id))
    return {"week_start": week_start, "grid": _dump(pid)}


@router.post("/api/meal-plans/generate")
def generate(week_start: str, uid: int = Depends(current_user_id)):
    """Fill empty slots with diverse engine recommendations (no repeats)."""
    from backend.app.deps import STATE
    s = STATE
    prefs = T.get_profile(uid)
    base, adapt, eff, has_activity = T.get_engine_for_app_user(s, uid)
    if has_activity:
        recs, _ = adapt.recommend(eff, k=60, ablation="full")
        cands = [r["recipe_id"] for r in recs]
    else:
        from src.recommender.taste import onboarding_profile
        own = base.recommend_new_user(k=60, max_minutes=prefs.get("max_minutes"))
        cands = [r["recipe_id"] for r in own]
    saved = [r["recipe_id"] for r in appdb.fetch_all(
        "SELECT DISTINCT recipe_id FROM user_recipe_interactions WHERE user_id=? AND interaction_type='SAVE'", (uid,))]
    for rid in saved:
        if rid not in cands:
            cands.insert(0, rid)
    # dietary respect: drop disliked + avoided ingredients
    disliked = {r["recipe_id"] for r in appdb.fetch_all(
        "SELECT recipe_id FROM user_recipe_interactions WHERE user_id=? AND interaction_type='DISLIKE'", (uid,))}
    avoid = [a.lower() for a in prefs.get("avoid_ingredients", [])]
    from backend.app.deps import rmap as _rmap2
    rmap = _rmap2(s)
    picks, seen = [], set()
    for rid in cands:
        if rid in seen or rid in disliked or rid not in rmap.index:
            continue
        if avoid and any(a in str(rmap.loc[rid, "ingredients_text"]) for a in avoid):
            continue
        seen.add(rid)
        picks.append(rid)
        if len(picks) >= 21:
            break
    p = _plan(uid, week_start)
    pid = p["id"] if p else appdb.execute("INSERT INTO meal_plans (user_id, week_start) VALUES (?,?)", (uid, week_start))
    i = 0
    for d in DAYS:
        for sl in SLOTS:
            exists = appdb.fetch_one("SELECT recipe_id FROM meal_plan_items WHERE plan_id=? AND day=? AND slot=?", (pid, d, sl))
            if (not exists or not exists["recipe_id"]) and i < len(picks):
                appdb.execute("INSERT INTO meal_plan_items (plan_id, day, slot, recipe_id) VALUES (?,?,?,?)"
                              " ON CONFLICT(plan_id, day, slot) DO UPDATE SET recipe_id=excluded.recipe_id",
                              (pid, d, sl, picks[i]))
                i += 1
    return {"week_start": week_start, "grid": _dump(pid), "filled": i}
