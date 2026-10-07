"""Auth routes: register / login / me."""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend.app import db as appdb
from backend.app.auth import hash_password, make_token, verify_password, current_user_id
from fastapi import Depends

router = APIRouter(prefix="/api/auth", tags=["auth"])

FOODCOM_DEMO_LINK = 269575


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    demo: bool = False


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _public(user_row) -> dict:
    return {"id": user_row["id"], "name": user_row["name"], "email": user_row["email"],
            "has_preferences": appdb.fetch_one(
                "SELECT 1 FROM user_preferences WHERE user_id=?", (user_row["id"],)) is not None}


@router.post("/register")
def register(body: RegisterIn):
    email = body.email.strip().lower()
    if appdb.fetch_one("SELECT id FROM users WHERE email=?", (email,)):
        raise HTTPException(409, "An account with this email already exists")
    name = re.sub(r"\s+", " ", body.name.strip())[:80]
    uid = appdb.execute(
        "INSERT INTO users (name, email, password_hash, linked_foodcom_id) VALUES (?,?,?,?)",
        (name, email, hash_password(body.password),
         FOODCOM_DEMO_LINK if body.demo else None))
    return {"token": make_token(uid), "user": _public(appdb.fetch_one("SELECT * FROM users WHERE id=?", (uid,)))}


@router.post("/login")
def login(body: LoginIn):
    row = appdb.fetch_one("SELECT * FROM users WHERE email=?", (body.email.strip().lower(),))
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    return {"token": make_token(row["id"]), "user": _public(row)}


@router.get("/me")
def me(uid: int = Depends(current_user_id)):
    row = appdb.fetch_one("SELECT * FROM users WHERE id=?", (uid,))
    if not row:
        raise HTTPException(401, "Account no longer exists")
    return _public(row)


@router.post("/refresh")
def refresh(uid: int = Depends(current_user_id)):
    return {"token": make_token(uid)}
