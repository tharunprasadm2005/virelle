"""Profile + onboarding preferences (real user-provided data)."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from backend.app import db as appdb
from backend.app.auth import current_user_id, hash_password, verify_password
from src.recommender.taste import get_profile

router = APIRouter(tags=["profile"])

ALLOWED_DIETS = {"", "vegetarian", "non-vegetarian", "vegan", "eggetarian"}
CUISINE_CHOICES = ["indian", "south indian", "chinese", "italian", "mexican", "american", "other"]
PRIORITY_CHOICES = ["quick", "easy", "healthy", "high protein", "budget friendly"]


class PrefsIn(BaseModel):
    diet: str = ""
    cuisines: list[str] = Field(default_factory=list, max_length=20)
    priorities: list[str] = Field(default_factory=list, max_length=20)
    avoid_ingredients: list[str] = Field(default_factory=list, max_length=50)
    max_minutes: Optional[int] = Field(default=None, ge=5, le=1440)
    nutrition_goals: list[str] = Field(default_factory=list, max_length=10)


class ProfileIn(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


def _clean(vals, allowed=None):
    out = []
    for v in vals or []:
        s = str(v).strip().lower()[:40]
        if s and (allowed is None or s in allowed) and s not in out:
            out.append(s)
    return out


@router.get("/api/profile")
def get_profile_route(uid: int = Depends(current_user_id)):
    row = appdb.fetch_one("SELECT id, name, email, created_at FROM users WHERE id=?", (uid,))
    if not row:
        raise HTTPException(401, "Account no longer exists")
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "member_since": row["created_at"], "preferences": get_profile(uid)}


@router.put("/api/profile")
def update_profile(body: ProfileIn, uid: int = Depends(current_user_id)):
    if body.name is not None and body.name.strip():
        appdb.execute("UPDATE users SET name=?, updated_at=datetime('now') WHERE id=?",
                      (body.name.strip()[:80], uid))
    return get_profile_route(uid)


@router.post("/api/profile/password")
def change_password(body: PasswordIn, uid: int = Depends(current_user_id)):
    row = appdb.fetch_one("SELECT * FROM users WHERE id=?", (uid,))
    if not verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(403, "Current password is incorrect")
    appdb.execute("UPDATE users SET password_hash=?, updated_at=datetime('now') WHERE id=?",
                  (hash_password(body.new_password), uid))
    return {"ok": True}


@router.get("/api/preferences")
def get_prefs(uid: int = Depends(current_user_id)):
    return get_profile(uid)


@router.put("/api/preferences")
def put_prefs(body: PrefsIn, uid: int = Depends(current_user_id)):
    diet = body.diet.strip().lower()
    if diet not in ALLOWED_DIETS:
        raise HTTPException(422, f"diet must be one of {sorted(ALLOWED_DIETS)}")
    appdb.execute(
        "INSERT INTO user_preferences (user_id, diet, cuisines, priorities, avoid_ingredients, max_minutes, nutrition_goals, updated_at)"
        " VALUES (?,?,?,?,?,?,?,datetime('now'))"
        " ON CONFLICT(user_id) DO UPDATE SET diet=excluded.diet, cuisines=excluded.cuisines,"
        " priorities=excluded.priorities, avoid_ingredients=excluded.avoid_ingredients,"
        " max_minutes=excluded.max_minutes, nutrition_goals=excluded.nutrition_goals, updated_at=datetime('now')",
        (uid, diet, json.dumps(_clean(body.cuisines, set(CUISINE_CHOICES))),
         json.dumps(_clean(body.priorities, set(PRIORITY_CHOICES))),
         json.dumps(_clean(body.avoid_ingredients)), body.max_minutes,
         json.dumps(_clean(body.nutrition_goals, {"high protein", "lighter meals", "calorie aware", "balanced"}))))
    return get_profile(uid)
