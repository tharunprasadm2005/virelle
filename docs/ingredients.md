# Ingredient intelligence (Phase 1)

## Decision
`ingredient-parser` (strangetom, MIT, v2.8.0) used AS A LIBRARY for structured
qty/unit/name/preparation. Verified: API (`parse_ingredient` → `ParsedIngredient`
with `name[]/amount[]/preparation/size/comment`), failure modes (empty string
raises IndexError → guarded; unknown strings return `ok` with original kept).

## Architecture
- `src/ingredients/normalize.py` — rule-based canonical names (qty/unit strip,
  singularize, alias seed, prep-leader strip). Total coverage, no dependencies.
- `src/ingredients/parser.py` — CRF wrapper, never raises, preserves original.
- `scripts/build_ingredient_index.py` — frequency-ordered offline index with
  `--top-n` + `--resume`; emits `ingredient_index.csv` + meta stamp
  (parser/version/time/coverage). Current: 3,000 strings, 52.6% mention coverage.
- Read path: `STATE["ing_index"]` loaded at startup; `cards.detail` attaches
  `ingredients_structured` (index hit or rule fallback, original always kept);
  shopping from-recipe prefers parsed name+qty, else verbatim text.
- Live: `GET /api/ingredients/lookup?text=` (~190ms, single strings only).

## Limits (honest)
CRF at ~190ms/string cannot cover 473K uniques in-session; long tail uses the
rule normalizer. Compound lines ("blueberries, granulated sugar, vanilla yogurt")
parse as one unit — preserved verbatim downstream. NLTK data
`averaged_perceptron_tagger_eng` is a one-time setup download (README).

## Phase 2 — knowledge layer (`knowledge.py`, KB v1)
- Curated categories (~160 head items + suffix rules + `other` default), each with
  confidence + source (`virelle-curated-v1`, rule name, or default).
- FDA major-9 allergen triggers + gluten/vegetarian/vegan/alcohol flags.
- **Safety design:** allergen/diet screens run over the FULL raw line
  (`safety_tokens`, no comma cut) so compound lines can't hide chicken/milk;
  display names keep the head ingredient. Non-dairy-butter exceptions handled.
- Allergen output is detection-for-filtering with a disclaimer, never medical advice.
- Wired into: search diet filter (replaces old regex), shopping buckets
  (knowledge-first, keyword fallback), recipe `diet_estimate` (labeled estimated),
  `GET /api/ingredients/info`.

## Phase 3 — pantry (`pantry_items`, migration v2)
sndimg rejects HEAD, so the audit GETs headers-only (no bodies). 30K most
popular recipes checked: 22,782 alive. `cards.py` suppresses audited-dead URLs
(`image_ok=false`); unchecked ids keep legacy behavior; shelves prefer
live-photo recipes (personalized ranking untouched).
User-owned stock: label + CRF-parsed normalized name/qty/unit + knowledge
category + optional expiry + availability flag. Strict per-row ownership on all
5 endpoints (`GET /api/pantry`, POST/PUT/PATCH/DELETE items). Expiry validated
as YYYY-MM-DD; overbuilt spoilage tracking deliberately deferred. UI:
`frontend/pantry.html` (grouped by category, availability toggle); linked from
nav and from the shopping page's successor flow in Phase 4.

## Phase 4/5 — cook matching + shopping intelligence
- Offline `recipe_ingredient_names.sqlite` (6.35M rows; CRF names where indexed,
  rule fallback; `scripts/build_recipe_name_index.py`).
- `GET /api/cook/matches`: score = 0.5·coverage + 0.3·pref (CB-to-liked +
  aspect compat, engine pieces reused) + 0.2·quality; diet/time/dislike/avoid
  filters; weights in `src/config.py` (`COOK_W_*`). Missing → one-tap shopping.
- Shopping: normalized duplicate merge (same-unit numerics summed, else kept
  separate), pantry-stock exclusion, pantry→shopping move. UI: `cook.html`.

## Image audit (scripts/audit_images.py + image_audit.csv)

sndimg rejects HEAD, so the audit GETs headers-only (no bodies). 30K most
popular recipes checked: 22,782 alive. cards.py suppresses audited-dead URLs
(image_ok=false); unchecked ids keep legacy behavior; shelves prefer
live-photo recipes (personalized ranking untouched).

