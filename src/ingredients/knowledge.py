"""Curated ingredient knowledge: categories, synonyms, allergens, dietary flags.
Code-curated (reviewable, versioned here) — NOT scraped, NOT fabricated per-item
facts. Every detection carries source='virelle-curated-v1' and a confidence.
Allergen output is INGREDIENT DETECTION for filtering, never medical advice.

Version: VIRELLE-FOOD-KB v1 (2026-10-06). Allergen set follows the US FDA
major-9 (milk, egg, fish, crustacean shellfish, tree nuts, peanut, wheat, soy,
sesame) plus a gluten-grain dietary flag.
"""
import re

from src.ingredients import normalize as N

KB_VERSION = "virelle-food-kb-v1"
SOURCE = "virelle-curated-v1"

CATEGORIES = {
    "vegetable", "fruit", "dairy", "meat", "poultry", "fish", "shellfish", "egg",
    "grain", "legume", "nut", "seed", "herb", "spice", "oil", "sweetener",
    "condiment", "beverage", "other",
}

# normalized name -> category (curated head; suffix rules + "other" cover the tail)
_ITEM_CATEGORY = {
    "milk": "dairy", "butter": "dairy", "cheese": "dairy", "yogurt": "dairy",
    "yoghurt": "dairy", "cream": "dairy", "paneer": "dairy", "cottage cheese": "dairy",
    "mozzarella": "dairy", "parmesan cheese": "dairy", "cheddar cheese": "dairy",
    "sour cream": "dairy", "cream cheese": "dairy", "whey": "dairy", "ghee": "dairy",
    "chicken": "poultry", "turkey": "poultry", "duck": "poultry",
    "beef": "meat", "pork": "meat", "bacon": "meat", "ham": "meat", "sausage": "meat",
    "lamb": "meat", "veal": "meat", "venison": "meat", "ground beef": "meat",
    "salmon": "fish", "tuna": "fish", "cod": "fish", "tilapia": "fish",
    "shrimp": "shellfish", "crab": "shellfish", "lobster": "shellfish",
    "clam": "shellfish", "mussel": "shellfish", "oyster": "shellfish", "scallop": "shellfish",
    "egg": "egg", "egg white": "egg", "egg yolk": "egg",
    "flour": "grain", "rice": "grain", "oat": "grain", "oats": "grain",
    "wheat": "grain", "bread": "grain", "pasta": "grain", "noodle": "grain",
    "barley": "grain", "rye": "grain", "cornmeal": "grain", "couscous": "grain",
    "quinoa": "grain", "bulgur": "grain",
    "lentil": "legume", "chickpeas": "legume", "black bean": "legume",
    "kidney bean": "legume", "pea": "legume", "soybean": "legume", "tofu": "legume",
    "peanut": "nut", "almond": "nut", "walnut": "nut", "cashew": "nut",
    "pecan": "nut", "pistachio": "nut", "hazelnut": "nut", "coconut": "nut",
    "sesame seed": "seed", "sunflower seed": "seed", "chia seed": "seed",
    "flax seed": "seed", "poppy seed": "seed", "pumpkin seed": "seed",
    "tomato": "vegetable", "onion": "vegetable", "potato": "vegetable",
    "carrot": "vegetable", "spinach": "vegetable", "lettuce": "vegetable",
    "cabbage": "vegetable", "broccoli": "vegetable", "cauliflower": "vegetable",
    "bell pepper": "vegetable", "cucumber": "vegetable", "zucchini": "vegetable",
    "eggplant": "vegetable", "mushroom": "vegetable", "celery": "vegetable",
    "green bean": "vegetable", "asparagus": "vegetable", "corn": "vegetable",
    "sweet potato": "vegetable", "green onion": "vegetable", "garlic": "vegetable",
    "ginger": "vegetable", "coriander": "herb", "basil": "herb", "parsley": "herb",
    "oregano": "herb", "thyme": "herb", "rosemary": "herb", "mint": "herb",
    "cilantro": "herb", "dill": "herb", "sage": "herb", "bay leaf": "herb",
    "salt": "spice", "black pepper": "spice", "pepper": "spice", "cumin": "spice",
    "turmeric": "spice", "cinnamon": "spice", "paprika": "spice",
    "chili powder": "spice", "cayenne": "spice", "curry powder": "spice",
    "garam masala": "spice", "mustard seed": "spice", "cardamom": "spice",
    "clove": "spice", "nutmeg": "spice", "ginger powder": "spice",
    "sugar": "sweetener", "honey": "sweetener", "maple syrup": "sweetener",
    "brown sugar": "sweetener", "powdered sugar": "sweetener", "molasses": "sweetener",
    "olive oil": "oil", "vegetable oil": "oil", "canola oil": "oil",
    "coconut oil": "oil", "sesame oil": "oil", "cooking spray": "oil",
    "vinegar": "condiment", "soy sauce": "condiment", "ketchup": "condiment",
    "mustard": "condiment", "mayonnaise": "condiment", "hot sauce": "condiment",
    "worcestershire sauce": "condiment", "lemon juice": "fruit", "lime juice": "fruit",
    "orange juice": "fruit", "apple": "fruit", "banana": "fruit", "lemon": "fruit",
    "lime": "fruit", "orange": "fruit", "strawberry": "fruit", "blueberry": "fruit",
    "mango": "fruit", "pineapple": "fruit", "peach": "fruit", "avocado": "fruit",
    "water": "beverage", "coffee": "beverage", "tea": "beverage", "wine": "beverage",
    "beer": "beverage", "rum": "beverage", "brandy": "beverage",
}

_SUFFIX_CATEGORY = [
    ("cheese", "dairy"), ("milk", "dairy"), ("yogurt", "dairy"), ("cream", "dairy"),
    ("fish", "fish"), ("bean", "legume"), ("beans", "legume"), ("lentils", "legume"),
    ("nut", "nut"), ("nuts", "nut"), ("seed", "seed"), ("seeds", "seed"),
    ("pepper", "vegetable"), ("juice", "fruit"), ("flour", "grain"),
    ("sauce", "condiment"), ("oil", "oil"), ("syrup", "sweetener"),
    ("butter", "dairy"), ("cheese", "dairy"),
]

# allergen -> trigger tokens matched against normalized-name tokens
ALLERGENS = {
    "milk": {"milk", "cheese", "butter", "cream", "yogurt", "yoghurt", "whey", "paneer",
             "mozzarella", "parmesan", "cheddar", "ghee", "casein", "lactose"},
    "egg": {"egg", "eggs", "mayonnaise", "meringue", "albumin"},
    "fish": {"fish", "salmon", "tuna", "cod", "tilapia", "anchovy", "sardine", "trout",
             "haddock", "mackerel", "catfish", "bass", "snapper"},
    "shellfish": {"shrimp", "prawn", "crab", "lobster", "clam", "mussel", "oyster",
                  "scallop", "crawfish", "shellfish"},
    "peanut": {"peanut", "peanuts", "groundnut"},
    "tree_nut": {"almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut",
                 "brazil", "macadamia", "chestnut", "pine", "coconut"},
    "wheat": {"wheat", "flour", "bread", "pasta", "noodle", "noodles", "couscous",
              "bulgur", "semolina", "breadcrumbs", "cracker", "pastry"},
    "soy": {"soy", "soya", "tofu", "miso", "tempeh", "edamame"},
    "sesame": {"sesame", "tahini"},
}

GLUTEN_TOKENS = {"wheat", "barley", "rye", "flour", "bread", "pasta", "noodle",
                 "noodles", "couscous", "bulgur", "semolina", "breadcrumbs", "malt"}
MEAT_TOKENS = {"beef", "pork", "bacon", "ham", "sausage", "lamb", "veal", "venison",
               "meat", "pepperoni", "salami", "chorizo", "prosciutto", "gelatin"}
POULTRY_TOKENS = {"chicken", "turkey", "duck", "goose", "poultry"}
HONEY_TOKENS = {"honey"}
ALCOHOL_TOKENS = {"wine", "beer", "rum", "brandy", "whiskey", "vodka", "liqueur", "alcohol"}


def _tokens(name: str) -> set:
    return set(name.lower().split())


def safety_tokens(raw: str) -> set:
    """All singularized alphanumeric tokens of the FULL raw line (no comma cut).

    Used for allergen/diet SAFETY screening: a compound line
    ("..., boneless chicken, ...") must still trigger on chicken, even though
    the display name keeps only the head ingredient.
    """
    toks = re.findall(r"[a-zA-Z][a-zA-Z\-']*", str(raw or "").lower())
    return {N.singularize(t.strip("'")) for t in toks}


def allergens_for_raw(raw: str) -> list:
    toks = safety_tokens(raw)
    low = str(raw or "").lower()
    if any(b in low for b in ("peanut butter", "apple butter", "cocoa butter", "shea butter",
                              "almond butter", "cashew butter", "sunflower butter")):
        toks.discard("butter")
    return sorted(a for a, trig in ALLERGENS.items() if toks & trig)


def diet_flags_for_raw(raw: str) -> dict:
    """Conservative suitability screen over the whole raw line."""
    toks = safety_tokens(raw)
    low = str(raw or "").lower()
    if any(b in low for b in ("peanut butter", "apple butter", "cocoa butter", "shea butter",
                              "almond butter", "cashew butter", "sunflower butter")):
        toks.discard("butter")
    meat = bool(toks & (MEAT_TOKENS | POULTRY_TOKENS | set(ALLERGENS["fish"]) | set(ALLERGENS["shellfish"])))
    dairy = bool(toks & ALLERGENS["milk"])
    egg = bool(toks & ALLERGENS["egg"])
    honey = bool(toks & HONEY_TOKENS)
    gluten = bool(toks & GLUTEN_TOKENS)
    return {"vegetarian_ok": not meat, "vegan_ok": not (meat or dairy or egg or honey),
            "gluten_free_ok": not gluten, "contains_alcohol": bool(toks & ALCOHOL_TOKENS)}


# multi-word names where a dairy-sounding suffix is NOT dairy
_NON_DAIRY_BUTTERS = {"peanut butter", "apple butter", "cocoa butter", "shea butter",
                      "almond butter", "cashew butter", "sunflower butter"}


def category_of(normalized: str) -> tuple:
    """(category, confidence, how). Curated hit = 0.95, suffix rule = 0.7, default = other/0.3."""
    n = (normalized or "").strip().lower()
    if not n:
        return "other", 0.0, "empty"
    if n in _ITEM_CATEGORY:
        return _ITEM_CATEGORY[n], 0.95, "curated"
    if n in _NON_DAIRY_BUTTERS:
        return "nut" if "nut" in n or "peanut" in n or "almond" in n or "cashew" in n else "other", 0.7, "exception-rule"
    for suffix, cat in _SUFFIX_CATEGORY:
        if n == suffix or n.endswith(" " + suffix):
            return cat, 0.7, "suffix-rule"
    return "other", 0.3, "default"


def _match_tokens(name: str) -> set:
    toks = _tokens(name)
    if (name or "").strip().lower() in _NON_DAIRY_BUTTERS:
        toks.discard("butter")
    return toks


def allergens_of(normalized: str) -> list:
    toks = _match_tokens(normalized or "")
    return sorted(a for a, trig in ALLERGENS.items() if toks & trig)


def diet_flags(normalized: str) -> dict:
    """Estimated suitability from the ingredient NAME (not certified)."""
    toks = _tokens(normalized or "")
    meat = bool(toks & (MEAT_TOKENS | POULTRY_TOKENS | set(ALLERGENS["fish"]) | set(ALLERGENS["shellfish"])))
    dairy = "milk" in allergens_of(normalized)
    egg = "egg" in allergens_of(normalized)
    honey = bool(toks & HONEY_TOKENS)
    gluten = bool(toks & GLUTEN_TOKENS)
    return {"vegetarian_ok": not meat, "vegan_ok": not (meat or dairy or egg or honey),
            "gluten_free_ok": not gluten, "contains_alcohol": bool(toks & ALCOHOL_TOKENS)}


def describe(raw: str) -> dict:
    """Full knowledge record for one raw ingredient string."""
    name = N.normalize_name(raw)
    cat, conf, how = category_of(name)
    return {"text": raw, "name": name, "category": cat, "category_confidence": conf,
            "category_source": SOURCE if how == "curated" else f"{SOURCE}:{how}",
            "allergens": allergens_of(name), "diet": diet_flags(name),
            "kb_version": KB_VERSION}
