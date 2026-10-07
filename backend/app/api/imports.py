"""Recipe URL import (user-owned, attributed). SSRF-guarded fetch + parse."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app import db as appdb
from backend.app.auth import current_user_id
from src.recipes import importer as IMP

router = APIRouter(tags=["import"])


class ImportIn(BaseModel):
    url: str = Field(min_length=8, max_length=2000)


@router.post("/api/imports")
def import_recipe(body: ImportIn, uid: int = Depends(current_user_id)):
    try:
        rec = IMP.fetch_and_parse(body.url)
    except ValueError as e:
        raise HTTPException(422, str(e))
    iid = appdb.execute(
        "INSERT INTO imported_recipes (user_id, title, ingredients, instructions, servings,"
        " total_minutes, image_url, source_url, source_name) VALUES (?,?,?,?,?,?,?,?,?)",
        (uid, rec["title"], json.dumps(rec["ingredients"]), json.dumps(rec["instructions"]),
         rec["servings"], rec["total_time"] or None, rec["image_url"], rec["source_url"], rec["source_name"]))
    return {"id": iid, **rec, "imported": True}


@router.get("/api/imports")
def list_imports(uid: int = Depends(current_user_id)):
    rows = appdb.fetch_all("SELECT * FROM imported_recipes WHERE user_id=? ORDER BY created_at DESC", (uid,))
    out = []
    for r in rows:
        d = dict(r)
        d["ingredients"] = json.loads(d["ingredients"] or "[]")
        d["instructions"] = json.loads(d["instructions"] or "[]")
        d["imported"] = True
        out.append(d)
    return {"imports": out}


@router.delete("/api/imports/{import_id}")
def delete_import(import_id: int, uid: int = Depends(current_user_id)):
    row = appdb.fetch_one("SELECT id FROM imported_recipes WHERE id=? AND user_id=?", (import_id, uid))
    if not row:
        raise HTTPException(404, "Import not found")
    appdb.execute("DELETE FROM imported_recipes WHERE id=?", (import_id,))
    return {"ok": True}
