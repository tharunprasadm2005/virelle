"""Pantry-aware matching: normalized pantry names vs recipe ingredient names.

Pure functions over name sets. Ranking weights live in src/config.py
(COOK_*), documented and tunable. Personalization/quality/diet plug in
from the existing engine — this module only scores availability.
"""
from src.ingredients import normalize as N


def recipe_name_set(raw_ingredients, index_names=None):
    """Raw ingredient lines -> set of normalized names.

    Uses the offline CRF index names where available (index_names: raw.lower()->name),
    else the rule normalizer. Compound lines additionally contribute their full-line
    safety tokens so nothing silently disappears.
    """
    from src.ingredients import knowledge as K
    out = set()
    for raw in raw_ingredients or []:
        hit = (index_names or {}).get(str(raw).strip().lower())
        if hit and str(hit).strip().lower() not in ("", "nan"):
            out.add(str(hit).strip())
            continue
        n = N.normalize_name(raw)
        if n:
            out.add(n)
        out.update(t for t in K.safety_tokens(raw) if len(t) > 2)
    return out


def coverage(pantry_names, recipe_names):
    """(matched, total, ratio, missing_names). Empty recipe -> 0.0, never crashes."""
    r = set(recipe_names or [])
    if not r:
        return set(), set(), 0.0, set()
    p = {x.lower() for x in (pantry_names or [])}
    matched = {n for n in r if n in p}
    missing = r - matched
    return matched, set(r), len(matched) / len(r), missing
