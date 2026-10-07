# Nutrition (Phases 8–9)

## Two levels, never confused
- **Recipe-level (source-listed):** Food.com `Calories/ProteinContent/...` columns,
  exposed as `nutrition: {values, source: "recipe-listed"}` on every card/detail.
  Accurate-as-listed; UI note says "not medical advice"; missing → honest
  "Nutrition information isn't available for this recipe."
- **Ingredient-level (estimated):** `src/nutrition/usda.py` maps normalized names
  to per-100g nutrients ONLY from an optional local USDA Foundation snapshot
  (`data/external/usda_foundation.csv`, CC0). Absent snapshot → `available()==False`,
  lookups return None. Nothing is ever guessed.

## USDA evaluation
USDA FoodData Central (CC0, free key) is the right source; the full Foundation
download + FTS matching service is deferred (snapshot path exists, build script
pending) because recipe-level columns already cover filters/goals. No scraping.

## Goals as preferences (Phase 9)
`nutrition_goals` ∈ {high protein, lighter meals, calorie aware, balanced}:
stored in prefs, applied as gentle re-rank boosts on home (+0.2 protein-scaled,
+0.15 calorie-scaled) and as hard filters in search (`min_protein`,
`max_calories`). Preferences, never prescriptions. Goals echoed in responses.
