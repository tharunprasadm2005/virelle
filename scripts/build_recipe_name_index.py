"""Offline per-recipe normalized-name index into SQLite (fast pantry matching).

Source of names: CRF ingredient_index.csv where the raw line matches, else the
rule normalizer (+ safety tokens for compound lines). Output:
data/processed/recipe_ingredient_names.sqlite with:
  recipe_names(recipe_id INTEGER, name TEXT) indexed both ways.
Rebuild rarely; version-stamped in meta table.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ast
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from src import config
from src.ingredients import normalize as N
from src.ingredients import knowledge as K
from src.ingredients.match import recipe_name_set


def main():
    rec = pd.read_csv(config.DATA_PROCESSED_DIR / "recipes_processed.csv",
                      usecols=["recipe_id", "ingredients"])
    idx = {}
    p = config.DATA_PROCESSED_DIR / "ingredient_index.csv"
    if p.exists():
        ing = pd.read_csv(p, usecols=["raw", "name"])
        idx = {str(r).strip().lower(): str(n).strip() for r, n in zip(ing["raw"], ing["name"])
               if str(n).strip().lower() not in ("", "nan")}
    print(f"Loaded {len(rec)} recipes, {len(idx)} indexed names.")
    dbp = config.DATA_PROCESSED_DIR / "recipe_ingredient_names.sqlite"
    if dbp.exists():
        dbp.unlink()
    conn = sqlite3.connect(str(dbp))
    conn.execute("CREATE TABLE recipe_names (recipe_id INTEGER NOT NULL, name TEXT NOT NULL)");
    conn.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)");
    batch, n = [], 0
    for rid, v in zip(rec["recipe_id"], rec["ingredients"]):
        try:
            items = ast.literal_eval(v) if isinstance(v, str) else []
        except (ValueError, SyntaxError):
            items = []
        names = recipe_name_set([str(i) for i in items], idx) if items else set()
        for nm in names:
            batch.append((int(rid), nm))
        if len(batch) >= 20000:
            conn.executemany("INSERT INTO recipe_names VALUES (?,?)", batch)
            batch = []
        n += 1
        if n % 100000 == 0:
            print(f"  {n}/{len(rec)}")
    if batch:
        conn.executemany("INSERT INTO recipe_names VALUES (?,?)", batch)
    conn.execute("CREATE INDEX idx_rn_recipe ON recipe_names(recipe_id)")
    conn.execute("CREATE INDEX idx_rn_name ON recipe_names(name)")
    conn.execute("INSERT INTO meta VALUES ('built_at',?)",
                 (datetime.now(timezone.utc).isoformat(),))
    conn.execute("INSERT INTO meta VALUES ('n_recipes',?)", (str(len(rec)),))
    conn.commit()
    cnt = conn.execute("SELECT COUNT(*) FROM recipe_names").fetchone()[0]
    print(f"Wrote {dbp}: {cnt} rows.")
    conn.close()


if __name__ == "__main__":
    main()
