"""My Pantry: user-owned ingredient stock. Strict ownership on every route."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from backend.app import db as appdb
from backend.app.auth import current_user_id
from src.ingredients import normalize as N
from src.ingredients import parser as P
from src.ingredients import knowledge as K

router = APIRouter(tags=["pantry"])


class PantryIn(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    quantity: str = Field(default="", max_length=60)
    unit: str = Field(default="", max_length=30)
    expiry: Optional[str] = Field(default=None, max_length=10)


class PantryEdit(BaseModel):
    label: Optional[str] = Field(default=None, max_length=120)
    quantity: Optional[str] = Field(default=None, max_length=60)
    unit: Optional[str] = Field(default=None, max_length=30)
    expiry: Optional[str] = Field(default=None, max_length=10)
    available: Optional[bool] = None


def _enrich(label: str, quantity: str, unit: str) -> dict:
    """Parse + normalize a pantry label. CRF single-string cost (~190ms) is fine here."""
    from difflib import get_close_matches
    parsed = P.parse_one(label)
    name = N.normalize_name(parsed["name"] if parsed["ok"] and parsed.get("name") else label)
    corrected_from = ""
    try:
        from backend.app.deps import STATE
        vocab = set((STATE.get("ing_index") or {}).keys()) | set(K._ITEM_CATEGORY.keys())
        if name and name not in vocab:
            hit = get_close_matches(name, vocab, n=1, cutoff=0.82)
            if hit:
                corrected_from = name
                name = hit[0]
    except Exception:
        pass
    cat, _, _ = K.category_of(name)
    qty = quantity.strip()[:60]
    u = unit.strip()[:30]
    if not qty and parsed.get("quantity") is not None:
        qty = str(parsed["quantity"])
    if not u and parsed.get("unit"):
        u = str(parsed["unit"])[:30]
    return {"label": label.strip()[:120], "normalized_name": name[:120],
            "quantity": qty, "unit": u, "category": cat, "corrected_from": corrected_from}


def _split_parts(label: str) -> list:
    """Split multi-item input ('a, b; c') into separate labels. Never invents items."""
    import re
    return [p.strip()[:120] for p in re.split(r"[,;\n]+", label or "") if p.strip()]


def _check_expiry(expiry: str | None) -> str | None:
    if not expiry:
        return None
    try:
        date.fromisoformat(expiry.strip())
        return expiry.strip()
    except ValueError:
        raise HTTPException(422, "expiry must be YYYY-MM-DD")


@router.get("/api/pantry")
def list_pantry(uid: int = Depends(current_user_id)):
    rows = appdb.fetch_all("SELECT * FROM pantry_items WHERE user_id=? ORDER BY category, label", (uid,))
    return {"items": [dict(r) for r in rows]}


@router.post("/api/pantry/items")
def add_item(body: PantryIn, uid: int = Depends(current_user_id)):
    parts = _split_parts(body.label)
    if not parts:
        raise HTTPException(422, "Empty ingredient")
    exp = _check_expiry(body.expiry)
    items = []
    for part in parts:
        e = _enrich(part, body.quantity, body.unit)
        iid = appdb.execute(
            "INSERT INTO pantry_items (user_id, label, normalized_name, quantity, unit, category, expiry)"
            " VALUES (?,?,?,?,?,?,?)",
            (uid, e["label"], e["normalized_name"], e["quantity"], e["unit"], e["category"], exp))
        row = dict(appdb.fetch_one("SELECT * FROM pantry_items WHERE id=? AND user_id=?", (iid, uid)))
        if e.get("corrected_from"):
            row["corrected_from"] = e["corrected_from"]
        items.append(row)
    return {"items": items}


@router.put("/api/pantry/items/{item_id}")
def edit_item(item_id: int, body: PantryEdit, uid: int = Depends(current_user_id)):
    row = appdb.fetch_one("SELECT * FROM pantry_items WHERE id=? AND user_id=?", (item_id, uid))
    if not row:
        raise HTTPException(404, "Pantry item not found")
    label = body.label.strip()[:120] if body.label else row["label"]
    e = _enrich(label, body.quantity if body.quantity is not None else row["quantity"],
                body.unit if body.unit is not None else row["unit"])
    avail = row["available"] if body.available is None else (1 if body.available else 0)
    exp = _check_expiry(body.expiry) if body.expiry is not None else row["expiry"]
    appdb.execute("UPDATE pantry_items SET label=?, normalized_name=?, quantity=?, unit=?,"
                  " category=?, expiry=?, available=?, updated_at=datetime('now') WHERE id=?",
                  (e["label"], e["normalized_name"], e["quantity"], e["unit"], e["category"],
                   exp, avail, item_id))
    return dict(appdb.fetch_one("SELECT * FROM pantry_items WHERE id=?", (item_id,)))


@router.patch("/api/pantry/items/{item_id}/availability")
def toggle(item_id: int, uid: int = Depends(current_user_id)):
    row = appdb.fetch_one("SELECT * FROM pantry_items WHERE id=? AND user_id=?", (item_id, uid))
    if not row:
        raise HTTPException(404, "Pantry item not found")
    appdb.execute("UPDATE pantry_items SET available=?, updated_at=datetime('now') WHERE id=?",
                  (0 if row["available"] else 1, item_id))
    return dict(appdb.fetch_one("SELECT * FROM pantry_items WHERE id=?", (item_id,)))


@router.delete("/api/pantry/items/{item_id}")
def remove(item_id: int, uid: int = Depends(current_user_id)):
    row = appdb.fetch_one("SELECT * FROM pantry_items WHERE id=? AND user_id=?", (item_id, uid))
    if not row:
        raise HTTPException(404, "Pantry item not found")
    appdb.execute("DELETE FROM pantry_items WHERE id=?", (item_id,))
    return {"ok": True}
