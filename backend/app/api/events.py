"""Recommendation events: SHOWN (impressions) + OPENED. Skips are DERIVED
(shown minus opened), never stored — an impression is not a negative signal."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app import db as appdb
from backend.app.auth import current_user_id

router = APIRouter(tags=["events"])


class EventIn(BaseModel):
    recipe_id: int
    event_type: str = Field(pattern="^(SHOWN|OPENED)$")
    context: str = Field(default="", max_length=120)


class BatchIn(BaseModel):
    recipe_ids: list[int] = Field(max_length=200)
    context: str = Field(default="", max_length=120)


@router.post("/api/events")
def record(body: EventIn, uid: int = Depends(current_user_id)):
    appdb.execute("INSERT INTO recommendation_events (user_id, recipe_id, event_type, context)"
                  " VALUES (?,?,?,?)", (uid, body.recipe_id, body.event_type, body.context[:120]))
    return {"ok": True}


@router.post("/api/events/shown-batch")
def record_batch(body: BatchIn, uid: int = Depends(current_user_id)):
    if not body.recipe_ids:
        raise HTTPException(422, "Empty batch")
    for rid in body.recipe_ids[:200]:
        appdb.execute("INSERT INTO recommendation_events (user_id, recipe_id, event_type, context)"
                      " VALUES (?,?,?,?)", (uid, int(rid), "SHOWN", body.context[:120]))
    return {"ok": True, "recorded": len(body.recipe_ids[:200])}
