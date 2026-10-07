"""Auth: bcrypt hashing + JWT bearer tokens. No plaintext passwords, no secrets in code."""
import hashlib
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SECRET = os.getenv("TASTEFLOW_SECRET", "dev-only-change-me-in-production-0123456789abcdef")
ALGO = "HS256"
TOKEN_HOURS = 24 * 7

bearer = HTTPBearer(auto_error=False)


def _pre(raw: str) -> bytes:
    """SHA-256 pre-hash so arbitrary-length passwords fit bcrypt's 72-byte input."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest().encode()


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(_pre(raw), bcrypt.gensalt()).decode()


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pre(raw), hashed.encode())
    except (ValueError, TypeError):
        return False


def make_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, SECRET, algorithm=ALGO)


def current_user_id(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    if creds is None or not creds.credentials:
        raise HTTPException(401, "Login required")
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=[ALGO])
        return int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
