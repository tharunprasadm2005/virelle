"""Shopping list: CRUD + add-from-recipe (real ingredient text, never invented)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app import db as appdb
from backend.app.api.cards import _lst
from backend.app.auth import current_user_id

router = APIRouter(tags=["shopping"])

VEG = ["tomato", "onion", "potato", "carrot", "coriander", "spinach", "pepper", "beans", "peas",
       "cabbage", "mushroom", "garlic", "ginger", "lemon", "lime", "lettuce", "cucumber"]
DAIRY = ["milk", "paneer", "butter", "cheese", "yogurt", "curd", "cream", "ghee"]
SPICE = ["salt", "turmeric", "masala", "cumin", "chili", "chilli", "pepper", "coriander powder",
         "garam", "mustard", "oregano", "basil", "paprika"]


_SHOP_BUCKET = {"vegetable": "vegetables", "fruit": "fruit", "dairy": "dairy",
                "meat": "meat & fish", "poultry": "meat & fish", "fish": "meat & fish",
                "shellfish": "meat & fish", "egg": "dairy", "grain": "grains",
                "legume": "grains", "nut": "nuts & seeds", "seed": "nuts & seeds",
                "herb": "spices", "spice": "spices", "oil": "oils",
                "sweetener": "baking", "condiment": "condiments", "beverage": "beverages"}


def categorize(label: str) -> str:
    """Knowledge-based bucket with keyword fallback (never fails)."""
    try:
        from src.ingredients import knowledge as K
        from src.ingredients import normalize as _N
        cat, conf, _ = K.category_of(_N.normalize_name(label))
        if conf >= 0.7 and cat in _SHOP_BUCKET:
            return _SHOP_BUCKET[cat]
    except Exception:
        pass
    l = label.lower()
    if any(w in l for w in VEG):
        return "vegetables"
    if any(w in l for w in DAIRY):
        return "dairy"
    if any(w in l for w in SPICE):
        return "spices"
    return "other"


class AddIn(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    quantity: str = Field(default="", max_length=60)


@router.get("/api/shopping-list")
def get_list(uid: int = Depends(current_user_id)):
    rows = appdb.fetch_all("SELECT * FROM shopping_items WHERE user_id=? ORDER BY checked, created_at", (uid,))
    return {"items": [dict(r) for r in rows]}


@router.post("/api/shopping-list/items")
def add_item(body: AddIn, uid: int = Depends(current_user_id)):
    import re
    parts = [p.strip()[:120] for p in re.split(r"[,;\n]+", body.label or "") if p.strip()]
    if not parts:
        raise HTTPException(422, "Empty item")
    items = []
    for label in parts:
        iid = appdb.execute("INSERT INTO shopping_items (user_id, label, category, quantity) VALUES (?,?,?,?)",
                            (uid, label, categorize(label), body.quantity.strip()[:60]))
        items.append(dict(appdb.fetch_one("SELECT * FROM shopping_items WHERE id=?", (iid,))))
    return {"items": items}


@router.post("/api/shopping-list/from-recipe/{recipe_id}")
def from_recipe(recipe_id: int, uid: int = Depends(current_user_id)):
    from backend.app.deps import STATE
    rmap = STATE["recipes"].set_index("recipe_id")
    if recipe_id not in rmap.index:
        raise HTTPException(404, "Unknown recipe")
    idx = STATE.get("ing_index") or {}
    existing = {r["label"].lower() for r in appdb.fetch_all(
        "SELECT label FROM shopping_items WHERE user_id=? AND checked=0", (uid,))}
    stock = _pantry_stock(uid)  # pantry-aware: don't buy what you have
    added = 0
    for ing in _lst(rmap.loc[recipe_id, "ingredients"]):
        hit = idx.get(str(ing).strip().lower())
        if hit and hit.get("name"):
            label = hit["name"]
            qty = ""
            if hit.get("quantity") is not None:
                qty = f"{hit['quantity']} {hit.get('unit','')}".strip()
        else:
            label, qty = ing, ""  # unparsed: preserve original text verbatim
        if label[:120].lower() in stock:
            continue
        if label[:120].lower() not in existing:
            appdb.execute("INSERT INTO shopping_items (user_id, label, category, quantity, recipe_id) VALUES (?,?,?,?,?)",
                          (uid, label[:120], categorize(label), qty[:60], recipe_id))
            existing.add(label[:120].lower())
            added += 1
    return {"added": added}


@router.patch("/api/shopping-list/items/{item_id}")
def toggle(item_id: int, uid: int = Depends(current_user_id)):
    row = appdb.fetch_one("SELECT * FROM shopping_items WHERE id=? AND user_id=?", (item_id, uid))
    if not row:
        raise HTTPException(404, "Item not found")
    appdb.execute("UPDATE shopping_items SET checked=? WHERE id=?", (0 if row["checked"] else 1, item_id))
    return dict(appdb.fetch_one("SELECT * FROM shopping_items WHERE id=?", (item_id,)))


@router.delete("/api/shopping-list/items/{item_id}")
def remove(item_id: int, uid: int = Depends(current_user_id)):
    row = appdb.fetch_one("SELECT * FROM shopping_items WHERE id=? AND user_id=?", (item_id, uid))
    if not row:
        raise HTTPException(404, "Item not found")
    appdb.execute("DELETE FROM shopping_items WHERE id=?", (item_id,))
    return {"ok": True}


@router.post("/api/shopping-list/clear-completed")
def clear(uid: int = Depends(current_user_id)):
    appdb.execute("DELETE FROM shopping_items WHERE user_id=? AND checked=1", (uid,))
    return {"ok": True}


def _split_qty(qty: str):
    """'2.5 cups' -> (2.5, 'cups'); unparseable -> (None, original). Never raises."""
    import re
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(.*)$", (qty or "").strip())
    if not m:
        return None, (qty or "").strip()
    return float(m.group(1)), m.group(2).strip().lower()


@router.post("/api/shopping-list/merge-duplicates")
def merge(uid: int = Depends(current_user_id)):
    """Merge unchecked duplicates sharing a normalized name AND compatible units.

    Compatible = same unit string with numeric quantities (summed) — anything
    else (different units, free text) is kept separate. Never invents conversions.
    """
    from src.ingredients import normalize as N
    rows = appdb.fetch_all("SELECT * FROM shopping_items WHERE user_id=? AND checked=0 ORDER BY created_at", (uid,))
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(N.normalize_name(r["label"]) or r["label"].lower(), []).append(dict(r))
    merged, kept = 0, 0
    for name, items in groups.items():
        if len(items) < 2:
            kept += 1
            continue
        units = {(_split_qty(i["quantity"])[1]) for i in items}
        qtys = [_split_qty(i["quantity"])[0] for i in items]
        if len(units) == 1 and all(q is not None for q in qtys):
            total = sum(qtys)
            unit = next(iter(units))
            keep = items[0]
            appdb.execute("UPDATE shopping_items SET label=?, quantity=? WHERE id=?",
                          (name[:120], f"{total:g} {unit}".strip()[:60], keep["id"]))
            for extra in items[1:]:
                appdb.execute("DELETE FROM shopping_items WHERE id=?", (extra["id"],))
            merged += len(items) - 1
        kept += len(items)
    return {"merged": merged}


def _pantry_stock(uid) -> set:
    rows = appdb.fetch_all("SELECT normalized_name, label FROM pantry_items WHERE user_id=? AND available=1", (uid,))
    return {(r["normalized_name"] or r["label"]).strip().lower() for r in rows if (r["normalized_name"] or r["label"]).strip()}


@router.post("/api/shopping-list/from-pantry/{item_id}")
def from_pantry(item_id: int, uid: int = Depends(current_user_id)):
    """Move a pantry item onto the shopping list (pantry row is kept)."""
    row = appdb.fetch_one("SELECT * FROM pantry_items WHERE id=? AND user_id=?", (item_id, uid))
    if not row:
        raise HTTPException(404, "Pantry item not found")
    qty = f"{row['quantity']} {row['unit']}".strip()
    iid = appdb.execute("INSERT INTO shopping_items (user_id, label, category, quantity) VALUES (?,?,?,?)",
                        (uid, row["label"], row["category"], qty[:60]))
    return dict(appdb.fetch_one("SELECT * FROM shopping_items WHERE id=?", (iid,)))
