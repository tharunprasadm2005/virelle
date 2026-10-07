"""Collections/cookbooks: user-owned recipe lists (Food.com + imported refs)."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app import db as appdb
from backend.app.auth import current_user_id

router = APIRouter(tags=["collections"])


class CollIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class RenameIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ItemIn(BaseModel):
    recipe_id: int
    source: str = Field(default="foodcom", pattern="^(foodcom|imported)$")


def _own(cid: int, uid: int):
    row = appdb.fetch_one("SELECT * FROM collections WHERE id=? AND user_id=?", (cid, uid))
    if not row:
        raise HTTPException(404, "Collection not found")
    return row


def _check_recipe(recipe_id: int, source: str, uid: int):
    if source == "foodcom":
        from backend.app.deps import recipe_ids as _ids, STATE
        if recipe_id not in _ids(STATE):
            raise HTTPException(404, "Unknown recipe")
    else:
        if not appdb.fetch_one("SELECT id FROM imported_recipes WHERE id=? AND user_id=?", (recipe_id, uid)):
            raise HTTPException(404, "Unknown imported recipe")


@router.get("/api/collections")
def list_colls(uid: int = Depends(current_user_id)):
    rows = appdb.fetch_all(
        "SELECT c.*, COUNT(i.id) n FROM collections c LEFT JOIN collection_items i ON i.collection_id=c.id"
        " WHERE c.user_id=? GROUP BY c.id ORDER BY c.created_at", (uid,))
    return {"collections": [dict(r) for r in rows]}


@router.post("/api/collections")
def create_coll(body: CollIn, uid: int = Depends(current_user_id)):
    name = body.name.strip()[:80]
    try:
        cid = appdb.execute("INSERT INTO collections (user_id, name) VALUES (?,?)", (uid, name))
    except Exception:
        raise HTTPException(409, "A collection with this name already exists")
    return dict(appdb.fetch_one("SELECT * FROM collections WHERE id=?", (cid,)))


@router.put("/api/collections/{cid}")
def rename_coll(cid: int, body: RenameIn, uid: int = Depends(current_user_id)):
    _own(cid, uid)
    try:
        appdb.execute("UPDATE collections SET name=? WHERE id=?", (body.name.strip()[:80], cid))
    except Exception:
        raise HTTPException(409, "A collection with this name already exists")
    return dict(appdb.fetch_one("SELECT * FROM collections WHERE id=?", (cid,)))


@router.delete("/api/collections/{cid}")
def delete_coll(cid: int, uid: int = Depends(current_user_id)):
    _own(cid, uid)
    appdb.execute("DELETE FROM collection_items WHERE collection_id=?", (cid,))
    appdb.execute("DELETE FROM collections WHERE id=?", (cid,))
    return {"ok": True}


@router.get("/api/collections/{cid}")
def get_coll(cid: int, uid: int = Depends(current_user_id)):
    from backend.app.deps import STATE, rmap as _rmap
    from backend.app.api.cards import card
    _own(cid, uid)
    items = appdb.fetch_all("SELECT recipe_id, source FROM collection_items WHERE collection_id=?", (cid,))
    rmap = _rmap(STATE)
    out = []
    for it in items:
        if it["source"] == "foodcom" and it["recipe_id"] in rmap.index:
            c = card(rmap.loc[it["recipe_id"]], it["recipe_id"])
            c["source"] = "foodcom"
            out.append(c)
        elif it["source"] == "imported":
            r = appdb.fetch_one("SELECT * FROM imported_recipes WHERE id=? AND user_id=?", (it["recipe_id"], uid))
            if r:
                out.append({"recipe_id": r["id"], "name": r["title"], "source": "imported",
                            "image_url": r["image_url"] or None,
                            "ingredients": json.loads(r["ingredients"] or "[]")})
    coll = dict(appdb.fetch_one("SELECT * FROM collections WHERE id=?", (cid,)))
    coll["recipes"] = out
    return coll


@router.post("/api/collections/{cid}/items")
def add_item(cid: int, body: ItemIn, uid: int = Depends(current_user_id)):
    _own(cid, uid)
    _check_recipe(body.recipe_id, body.source, uid)
    try:
        appdb.execute("INSERT INTO collection_items (collection_id, recipe_id, source) VALUES (?,?,?)",
                      (cid, body.recipe_id, body.source))
    except Exception:
        raise HTTPException(409, "Already in this collection")
    return {"ok": True}


@router.delete("/api/collections/{cid}/items")
def remove_item(cid: int, recipe_id: int, source: str = "foodcom", uid: int = Depends(current_user_id)):
    _own(cid, uid)
    appdb.execute("DELETE FROM collection_items WHERE collection_id=? AND recipe_id=? AND source=?",
                  (cid, recipe_id, source))
    return {"ok": True}
