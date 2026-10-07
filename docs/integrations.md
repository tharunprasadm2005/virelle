# Open-source integrations log

Rule: USE AS LIBRARY when possible; concepts otherwise; never clone apps.
Every entry: repo / version / license / purpose / integration point / why.

| Project | Repo | License | Purpose here | Status |
|---|---|---|---|---|
| ingredient-parser | github.com/strangetom/ingredient-parser (v2.8.0, PyPI `ingredient-parser-nlp`) | MIT (verified) | Structured qty/unit/name/preparation from raw strings; used AS LIBRARY via `src/ingredients/parser.py` wrapper (never raises, preserves original). Requires one-time NLTK data `averaged_perceptron_tagger_eng` (see README setup). Offline index `data/processed/ingredient_index.csv` + meta stamp. | ✅ Integrated Phase 1 |
| sentence-transformers + FAISS | github.com/UKPLab/sentence-transformers (Apache-2.0) + github.com/facebookresearch/faiss (MIT) | Apache-2.0 / MIT | MiniLM-L6-v2 semantic sidecar over recipe text; used AS LIBRARY via `src/recommender/semantic_search.py` (lazy load) + offline `scripts/build_semantic_index.py`. TF-IDF preserved; fusion weights documented in `src/config.py`. | ✅ Integrated Phase 6/7 |
| USDA FoodData Central | fdc.nal.usda.gov (CC0 public domain) | CC0 | Evaluated: right source for ingredient-level nutrition. Integrated as optional-snapshot layer (`src/nutrition/usda.py`, unavailable-without-snapshot, never guessed). Full snapshot + FTS matching deferred; recipe-level dataset columns serve filters/goals today. | 🟡 Evaluated, partial (Phase 8) |
| recipe-scrapers | github.com/hhursev/recipe-scrapers (v15.12.0) | MIT | URL → title/ingredients/instructions/servings/time/image; used AS LIBRARY via `src/recipes/importer.py` with SSRF guard (public-IP-only, timeout, size cap, UA) + stored attribution. `imported_recipes` table (migration v4). | ✅ Integrated Phase 10 |

Candidate queue (evaluate in their phase, verify license + API before use):
- ingredient-parser (`strangetom/ingredient-parser`, MIT) → Phase 1
- recipe-scrapers (`hhursev/recipe-scrapers`, MIT) → Phase 10
- sentence-transformers + FAISS (Apache-2.0 / MIT) → Phase 6
- USDA FoodData Central data/API (CC0) → Phase 8
- Mealie / Tandoor Recipes → concepts only (AGPL / terms-risky), Phases 5/11
