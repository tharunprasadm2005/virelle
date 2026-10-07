"""Rule-based ingredient-name normalization. Fast, dependency-free, total coverage.

Maps any raw string -> canonical name. Structured qty/unit comes from
parser.py (CRF) where available; this module never fails and never invents data.
"""
import re
from fractions import Fraction

_UNITS = {"cup", "cups", "tablespoon", "tablespoons", "tbsp", "tbs", "teaspoon", "teaspoons",
          "tsp", "ounce", "ounces", "oz", "pound", "pounds", "lb", "lbs", "gram", "grams", "g",
          "kg", "kilogram", "milliliter", "milliliters", "ml", "liter", "liters", "l", "pint",
          "pints", "quart", "quarts", "gallon", "gallons", "clove", "cloves", "slice", "slices",
          "can", "cans", "package", "packages", "pkg", "bunch", "bunches", "pinch", "dash",
          "sprig", "sprigs", "stalk", "stalks", "piece", "pieces", "strip", "strips"}

_NUM = re.compile(r"^[\d\s\/\.\-¼½¾⅓⅔⅛⅜⅝⅞%]+$")
_PARENS = re.compile(r"\([^)]*\)")


def strip_quantity_prefix(text: str) -> str:
    toks = text.strip().split()
    i = 0
    while i < len(toks) and (_NUM.match(toks[i]) or toks[i].lower().rstrip(".,") in _UNITS
                             or toks[i].lower() in ("of", "a", "an")):
        i += 1
    return " ".join(toks[i:])


def singularize(word: str) -> str:
    w = word.strip().lower()
    if len(w) > 4 and w.endswith("oes"):  # tomatoes, potatoes
        return w[:-2]
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("es") and w[-3] in "sxz" or w.endswith(("ches", "shes")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


# leading preparation/state adjectives safe to drop from the FRONT only
PREP_LEADERS = {"chopped", "diced", "minced", "sliced", "grated", "crushed", "fresh",
                "dried", "ground", "powdered", "frozen", "thawed", "cooked", "raw",
                "large", "medium", "small", "ripe", "whole"}


# curated alias map (Phase 2 owns the full knowledge layer; minimal seed here)
ALIASES = {
    "scallion": "green onion", "scallions": "green onion",
    "spring onion": "green onion", "coriander leaves": "coriander",
    "cilantro": "coriander", "aubergine": "eggplant", "courgette": "zucchini",
    "capsicum": "bell pepper", "chickpea": "chickpeas", "garbanzo": "chickpeas",
    "garbanzo bean": "chickpeas", "mince": "ground beef",
}


def normalize_name(raw: str) -> str:
    """Raw ingredient text -> canonical name. Empty in -> empty out (never fails)."""
    if raw is None:
        return ""
    s = str(raw).strip().lower()
    if not s:
        return ""
    s = _PARENS.sub(" ", s)
    s = strip_quantity_prefix(s)
    s = re.sub(r"\s+", " ", s).strip(" ,.-")
    # drop trailing preparation adjectives that survived prefix stripping
    s = re.sub(r",.*$", "", s).strip()
    toks = s.split()
    while toks and toks[0] in PREP_LEADERS:
        toks = toks[1:]
    s = " ".join(toks)
    if s in ALIASES:
        return ALIASES[s]
    toks = [singularize(t) for t in s.split()]
    out = " ".join(toks)
    return ALIASES.get(out, out)
