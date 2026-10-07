"""Live single-string ingredient lookup (pantry inputs, imports)."""
from fastapi import APIRouter, Query

from src.ingredients import normalize as N
from src.ingredients import parser as P

router = APIRouter(tags=["ingredients"])


@router.get("/api/ingredients/lookup")
def lookup(text: str = Query(min_length=1, max_length=200)):
    parsed = P.parse_one(text)
    name = N.normalize_name(parsed["name"] if parsed["ok"] and parsed.get("name") else text)
    return {"text": text, "name": name, "quantity": parsed.get("quantity"),
            "quantity_max": parsed.get("quantity_max"), "unit": parsed.get("unit", ""),
            "preparation": parsed.get("preparation", ""), "parsed": bool(parsed["ok"])}


@router.get("/api/ingredients/info")
def info(name: str = Query(min_length=1, max_length=200)):
    """Curated knowledge for one ingredient name (category/allergens/diet)."""
    from src.ingredients import knowledge as K
    rec = K.describe(name)
    rec["disclaimer"] = "Ingredient detection for filtering; not medical advice."
    return rec
