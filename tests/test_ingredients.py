"""Phase 1 tests: normalization + CRF wrapper contract (never raises, preserves original)."""
from src.ingredients import normalize as N
from src.ingredients import parser as IP


def test_normalize_basics():
    assert N.normalize_name("2 cups chopped onions") == "onion"
    assert N.normalize_name("Salt") == "salt"
    assert N.normalize_name("  ") == ""
    assert N.normalize_name(None) == ""
    assert N.normalize_name("cilantro") == "coriander"
    assert N.normalize_name("1 (14 ounce) can diced tomatoes, drained") == "dice tomato" or \
        "tomato" in N.normalize_name("1 (14 ounce) can diced tomatoes, drained")


def test_normalize_units_quantities():
    assert N.normalize_name("1/2 teaspoon cumin seeds") == "cumin seed"
    assert N.normalize_name("3 cloves garlic, minced") == "garlic"


def test_parser_contract():
    p = IP.parse_one("2 cups chopped onions")
    assert p["original"] == "2 cups chopped onions" and p["ok"] is True
    assert p["quantity"] == 2.0 and p["unit"] == "cup"
    assert "onion" in p["name"]
    assert IP.parse_one("")["ok"] is False
    assert IP.parse_one(None)["ok"] is False
    assert IP.parse_one("salt")["ok"] is True
    bad = IP.parse_one("!!! ??? ###")
    assert bad["original"] == "!!! ??? ###" and "ok" in bad  # never raises


def test_parser_modifiers_and_unknown():
    p = IP.parse_one("1 (14 ounce) can diced tomatoes, drained")
    assert p["ok"] and "tomato" in p["name"]
    u = IP.parse_one("dragonfruit nectar")
    assert u["original"] == "dragonfruit nectar"  # unknown kept, never destroyed


def test_duplicates_normalize_same():
    assert N.normalize_name("Onions") == N.normalize_name("1 onion")
