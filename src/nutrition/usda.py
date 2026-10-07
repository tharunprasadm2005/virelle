"""USDA FoodData Central mapping layer (CC0 public data).

Design: ingredient name -> per-100g nutrients from an OPTIONAL local snapshot
(data/external/usda_foundation.csv). Without the snapshot every function
returns 'unavailable' — values are NEVER fabricated or guessed.

To enable: download Foundation Foods from https://fdc.nal.usda.gov/download-datasets.html
(or use a free API key at runtime), place the CSV at data/external/usda_foundation.csv,
and rerun scripts/build_nutrition_cache.py (future). Recipe-level nutrition
shown in the product always comes from the Food.com columns (source-listed).
"""
import pandas as pd

from src import config

SNAPSHOT = config.DATA_EXTERNAL_DIR / "usda_foundation.csv"
_cache = None


def available() -> bool:
    return SNAPSHOT.exists()


def _load():
    global _cache
    if _cache is None:
        if not available():
            raise FileNotFoundError("USDA snapshot missing at data/external/usda_foundation.csv")
        _cache = pd.read_csv(SNAPSHOT)
    return _cache


def lookup_ingredient(name: str):
    """Per-100g nutrients for a normalized ingredient name, or None if unavailable."""
    if not available():
        return None
    df = _load()
    hits = df[df["description"].str.lower() == str(name).lower()]
    if hits.empty:
        return None
    r = hits.iloc[0]
    return {"source": "usda-foundation-snapshot", **{c: r[c] for c in
              ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g"] if c in df.columns}}
