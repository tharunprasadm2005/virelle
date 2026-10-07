"""Shared recipe-card shaping from REAL Food.com processed rows. No fake data."""
import ast

# image-liveness policy (populated from STATE at startup; empty = legacy behavior)
_IMAGE_DEAD: set = set()
_IMAGE_LIVE: set = set()


def set_image_policy(dead=None, live=None):
    global _IMAGE_DEAD, _IMAGE_LIVE
    _IMAGE_DEAD = set(dead or [])
    _IMAGE_LIVE = set(live or [])


def image_ok(recipe_id: int) -> bool | None:
    """True=audited alive, False=audited dead, None=unchecked (serve legacy-style)."""
    if recipe_id in _IMAGE_DEAD:
        return False
    if recipe_id in _IMAGE_LIVE:
        return True
    return None


def _lst(v):
    if isinstance(v, list):
        return [str(x) for x in v]
    if v is None or (not isinstance(v, str)):
        return []
    s = v.strip()
    if not s or s == "nan":
        return []
    try:
        p = ast.literal_eval(s)
        if isinstance(p, list):
            return [str(x) for x in p]
    except (ValueError, SyntaxError):
        pass
    return [s]


def _num(d, key, default=None):
    try:
        f = float(d.get(key))
    except (TypeError, ValueError):
        return default
    return default if f != f else f  # NaN -> default (JSON-safe)


def _rowdict(row):
    if isinstance(row, dict):
        return row
    try:
        return dict(row.to_dict())
    except (AttributeError, TypeError):
        return {}


def card(row, rid=None) -> dict:
    d = _rowdict(row)
    img = d.get("image_url")
    img = "" if img is None or str(img) in ("", "nan") else str(img)
    try:
        mins = int(d.get("minutes"))
    except (TypeError, ValueError):
        mins = None
    tags = _lst(d.get("tags"))[:8]
    if rid is None:
        try:
            rid = int(d.get("recipe_id"))
        except (TypeError, ValueError):
            rid = -1
    if rid in _IMAGE_DEAD:
        img = ""  # audited dead URL: suppress so clients never request it
    import html as _html
    nut = {}
    for col, key in [("Calories", "calories"), ("ProteinContent", "protein"),
                     ("CarbohydrateContent", "carbs"), ("FatContent", "fat"),
                     ("FiberContent", "fiber"), ("SugarContent", "sugar"),
                     ("SodiumContent", "sodium")]:
        v = _num(d, col)
        if v is not None:
            nut[key] = v
    return {"recipe_id": int(rid),
            "name": _html.unescape(str(d.get("name", ""))),
            "minutes": mins, "servings": _num(d, "RecipeServings"),
            "rating": _num(d, "AggregatedRating"), "review_count": _num(d, "ReviewCount", 0),
            "calories": _num(d, "Calories"), "image_url": img or None, "tags": tags,
            "description": str(d.get("description") or "")[:300],
            "nutrition": {"values": nut, "source": "recipe-listed" if nut else None,
                          "note": "As listed in the Food.com dataset; not medical advice." if nut else
                          "Nutrition information isn't available for this recipe."}}


def detail(row, ingredients=None, instructions=None) -> dict:
    d = _rowdict(row)
    out = card(d)
    out["ingredients"] = _lst(d.get("ingredients"))
    out["instructions"] = _lst(d.get("RecipeInstructions"))
    out["description_full"] = str(d.get("description") or "")
    try:
        from src.ingredients import knowledge as K
        from src.ingredients import normalize as _N
        allergens, veg_ok, vegan_ok, gf_ok = set(), True, True, True
        for raw in out["ingredients"]:
            # safety screen over the FULL raw line (compound lines included)
            allergens.update(K.allergens_for_raw(raw))
            f = K.diet_flags_for_raw(raw)
            veg_ok &= f["vegetarian_ok"]
            vegan_ok &= f["vegan_ok"]
            gf_ok &= f["gluten_free_ok"]
        # ESTIMATED from ingredient names — not certified; UI must label as such
        out["diet_estimate"] = {"vegetarian": bool(veg_ok), "vegan": bool(vegan_ok),
                                "gluten_free": bool(gf_ok),
                                "allergens_detected": sorted(allergens),
                                "disclaimer": "Estimated from the ingredient list; not medical advice."}
    except Exception:
        out["diet_estimate"] = None
    try:
        from backend.app.deps import STATE
        idx = STATE.get("ing_index") or {}
        structured = []
        for raw in out["ingredients"]:
            hit = idx.get(str(raw).strip().lower())
            if hit:
                structured.append({"text": raw, "name": hit.get("name", raw),
                                   "quantity": hit.get("quantity"), "unit": hit.get("unit", ""),
                                   "preparation": hit.get("preparation", "")})
            else:
                from src.ingredients import normalize as _N
                structured.append({"text": raw, "name": _N.normalize_name(raw),
                                   "quantity": None, "unit": "", "preparation": ""})
        out["ingredients_structured"] = structured
    except Exception:
        out["ingredients_structured"] = [{"text": raw} for raw in out["ingredients"]]
    return out
