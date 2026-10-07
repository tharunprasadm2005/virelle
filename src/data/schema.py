"""Dataset discovery + schema validation for the REAL Food.com dataset.

Primary expected files in data/raw/:
    RAW_recipes.csv, RAW_interactions.csv
Also recognised (same dataset mirrored under other names):
    recipes.csv / Reviews.csv etc.

Column names are NOT hard-coded: we normalise case/whitespace and accept
known variants, then map to canonical names. Anything unrecognised raises
a clear error telling the user what was found vs expected.
"""
from pathlib import Path
import pandas as pd
from src import config

RECIPE_FILE_CANDIDATES = config.EXPECTED_RECIPE_FILES
INTERACTION_FILE_CANDIDATES = config.EXPECTED_INTERACTION_FILES

# canonical -> accepted variants (lowercased, stripped)
RECIPE_COLUMNS = {
    "recipe_id": ["id", "recipe_id", "recipeid"],
    "name": ["name", "recipename", "title"],
    "ingredients": ["ingredients", "ingredients_list", "ingredient", "recipeingredientparts"],
    "tags": ["tags", "tag", "keywords", "recipecategory"],
    "nutrition": ["nutrition", "nutrients"],
    "minutes": ["minutes", "totaltime", "cooktime", "preptime", "time"],
    "description": ["description", "summary", "recipeinstructions", "instructions", "steps"],
    "n_steps": ["n_steps", "nsteps", "numsteps"],
}
INTERACTION_COLUMNS = {
    "user_id": ["user_id", "userid", "authorid"],
    "recipe_id": ["recipe_id", "recipeid", "id"],
    "rating": ["rating", "stars", "aggregatedrating"],
    "review": ["review", "reviewtext", "text", "comment"],
    "date": ["date", "datesubmitted", "datemodified", "datetime", "timestamp", "reviewdate"],
}

REQUIRED_RECIPE = ["recipe_id"]  # name etc. optional (filled with defaults)
REQUIRED_INTERACTION = ["user_id", "recipe_id", "rating"]


class DatasetNotFoundError(FileNotFoundError):
    pass


class SchemaError(ValueError):
    pass


def _norm(cols):
    return {str(c).strip().lower(): c for c in cols}


def resolve_dataset_files(raw_dir=None):
    raw_dir = Path(raw_dir or config.DATA_RAW_DIR)
    recipe_path = next((raw_dir / f for f in RECIPE_FILE_CANDIDATES if (raw_dir / f).exists()), None)
    inter_path = next((raw_dir / f for f in INTERACTION_FILE_CANDIDATES if (raw_dir / f).exists()), None)
    # fallback: any csv containing 'recip' vs 'interact|review' in name
    if recipe_path is None or inter_path is None:
        csvs = list(raw_dir.glob("*.csv")) if raw_dir.exists() else []
        for p in csvs:
            n = p.name.lower()
            if recipe_path is None and ("recip" in n):
                recipe_path = p
            if inter_path is None and ("interact" in n or "review" in n):
                inter_path = p
    missing = []
    if recipe_path is None:
        missing.append(f"recipe file (one of {RECIPE_FILE_CANDIDATES})")
    if inter_path is None:
        missing.append(f"interaction/review file (one of {INTERACTION_FILE_CANDIDATES})")
    if missing:
        found = sorted(p.name for p in raw_dir.glob("*.csv")) if raw_dir.exists() else []
        raise DatasetNotFoundError(
            config.MISSING_DATA_MSG + f" Missing: {', '.join(missing)}. Found in data/raw/: {found or 'nothing'}."
        )
    return recipe_path, inter_path


def map_columns(df: pd.DataFrame, spec: dict, label: str):
    norm = _norm(df.columns)
    mapping = {}
    for canonical, variants in spec.items():
        for v in variants:
            if v in norm:
                mapping[norm[v]] = canonical
                break
    return mapping


def validate_and_canonicalise(df: pd.DataFrame, spec: dict, required: list, label: str):
    mapping = map_columns(df, spec, label)
    missing = [c for c in required if c not in mapping.values()]
    if missing:
        raise SchemaError(
            f"{label}: missing required columns {missing}. "
            f"Found columns: {list(df.columns)}. "
            f"Accepted variants: {spec}. Inspect your CSV header row."
        )
    out = df.rename(columns=mapping)
    return out, mapping
