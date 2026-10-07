"""Phase 2 tests: categories, synonyms, allergens, diet flags, exclusions."""
from src.ingredients import knowledge as K


def test_categories():
    assert K.category_of("tomato")[0] == "vegetable"
    assert K.category_of("paneer")[0] == "dairy"
    assert K.category_of("chicken")[0] == "poultry"
    assert K.category_of("quinoa")[0] == "grain"
    assert K.category_of("dragonfruit nectar")[0] == "other"
    assert K.category_of("")[0] == "other"


def test_synonyms_and_aliases():
    from src.ingredients import normalize as N
    assert N.normalize_name("scallions") == "green onion"
    assert K.category_of(N.normalize_name("scallions"))[0] == "vegetable"


def test_allergens():
    assert "peanut" in K.allergens_of("peanut")
    assert "milk" in K.allergens_of("parmesan cheese")
    assert "shellfish" in K.allergens_of("shrimp")
    assert K.allergens_of("rice") == []
    assert "sesame" in K.allergens_of("sesame oil")


def test_diet_flags():
    assert K.diet_flags("chicken")["vegetarian_ok"] is False
    assert K.diet_flags("milk")["vegetarian_ok"] is True
    assert K.diet_flags("milk")["vegan_ok"] is False
    assert K.diet_flags("tofu")["vegan_ok"] is True
    assert K.diet_flags("bread")["gluten_free_ok"] is False
    assert K.diet_flags("rice")["gluten_free_ok"] is True


def test_describe_contract():
    d = K.describe("2% milk")
    assert d["name"] == "milk" and d["category"] == "dairy"
    assert "milk" in d["allergens"] and d["kb_version"].startswith("virelle-food-kb-v")
    assert d["category_source"].startswith("virelle-curated")


def test_compound_line_safety():
    line = "saffron, milk, hot green chili peppers, onions, garlic, boneless chicken, salt"
    assert K.diet_flags_for_raw(line)["vegetarian_ok"] is False
    assert K.diet_flags_for_raw(line)["vegan_ok"] is False
    assert "milk" in K.allergens_for_raw(line)
    assert K.diet_flags_for_raw("2 cups rice")["vegan_ok"] is True


def test_non_dairy_butters():
    assert K.category_of("peanut butter")[0] == "nut"
    assert K.allergens_of("peanut butter") == ["peanut"]
    assert "milk" in K.allergens_of("butter")
    assert K.allergens_for_raw("2 tbsp peanut butter") == ["peanut"]
    assert K.diet_flags_for_raw("peanut butter sandwich")["vegan_ok"] is True
