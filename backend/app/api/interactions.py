"""Interactions (like/dislike/save/cook/rate/review) + favorites.

Every row is a genuine app-user action with a real timestamp — these are the
signals the personalization bridge feeds to the engine.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from backend.app import db as appdb
from backend.app.auth import current_user_id

router = APIRouter(tags=["interactions"])

KINDS = {"LIKE", "DISLIKE", "SAVE", "UNSAVE", "COOKED", "RATED", "REVIEW"}


class InteractIn(BaseModel):
    interaction_type: str
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    review_text: str = Field(default="", max_length=5000)


def _recipe_exists(recipe_id: int, state) -> bool:
    ids = state.get("recipe_ids")
    if ids is not None:
        return recipe_id in ids
    return recipe_id in set(state["recipes"]["recipe_id"].tolist())


@router.post("/api/interactions/{recipe_id}")
def interact(recipe_id: int, body: InteractIn, uid: int = Depends(current_user_id)):
    from backend.app.deps import STATE
    kind = body.interaction_type.strip().upper()
    if kind not in KINDS:
        raise HTTPException(422, f"interaction_type must be one of {sorted(KINDS)}")
    if kind == "RATED" and not body.rating:
        raise HTTPException(422, "rating is required for RATED")
    if not _recipe_exists(recipe_id, STATE):
        raise HTTPException(404, "Unknown recipe")
    review = body.review_text.strip()[:5000]
    appdb.execute(
        "INSERT INTO user_recipe_interactions (user_id, recipe_id, interaction_type, rating, review_text, created_at)"
        " VALUES (?,?,?,?,?,?)",
        (uid, recipe_id, kind, body.rating, review, datetime.now().isoformat(timespec="seconds")))
    if kind == "UNSAVE":
        appdb.execute("DELETE FROM user_recipe_interactions WHERE user_id=? AND recipe_id=? AND interaction_type='SAVE'",
                      (uid, recipe_id))
    return {"ok": True}


@router.get("/api/favorites")
def favorites(uid: int = Depends(current_user_id)):
    from backend.app.deps import STATE
    from backend.app.api.cards import card
    rows = appdb.fetch_all(
        "SELECT DISTINCT recipe_id FROM user_recipe_interactions WHERE user_id=? AND interaction_type='SAVE'"
        " AND recipe_id NOT IN (SELECT recipe_id FROM user_recipe_interactions WHERE user_id=? AND interaction_type='UNSAVE')",
        (uid, uid))
    rmap = STATE["recipes"].set_index("recipe_id")
    out = []
    for r in rows:
        rid = int(r["recipe_id"])
        if rid in rmap.index:
            out.append(card(rmap.loc[rid], rid))
    return {"favorites": out}


@router.get("/api/interactions/mine")
def mine(uid: int = Depends(current_user_id)):
    rows = appdb.fetch_all(
        "SELECT recipe_id, interaction_type, rating, created_at FROM user_recipe_interactions"
        " WHERE user_id=? ORDER BY created_at DESC LIMIT 200", (uid,))
    return {"interactions": [dict(r) for r in rows]}
