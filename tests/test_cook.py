"""Phase 4 tests: coverage math + cook endpoints on fixture-scale sqlite index."""
import os
import sqlite3
import pandas as pd
from fastapi.testclient import TestClient

TmpDB = os.path.join(os.path.dirname(__file__), "test_cook_tmp.db")
TmpIdx = os.path.join(os.path.dirname(__file__), "test_names.sqlite")
for f in (TmpDB, TmpIdx):
    if os.path.exists(f):
        os.remove(f)
for f in (TmpDB, TmpIdx):
    if os.path.exists(f):
        os.remove(f)

from pathlib import Path
from backend.app import db as appdb
appdb.DB_PATH = Path(TmpDB)
from backend.app import migrations as appmig
appmig.migrate()

import pytest


@pytest.fixture(autouse=True)
def _isolated_db():
    appdb.DB_PATH = Path(TmpDB)
    yield

from src.data import preprocess as P
from src.data import features as F
from src.recommender.baseline import BaselineRecommender
from src.recommender.hybrid import AdaptiveRecommender
from src.recommender import aspect_model as A
from tests.fixtures import tiny_recipes, tiny_interactions
from src.ingredients.match import recipe_name_set, coverage
import backend.app.main as M
import backend.app.api.cook as cookmod


def _state():
    r = P.preprocess_recipes(tiny_recipes())
    i = P.preprocess_interactions(tiny_interactions(), valid_recipe_ids=set(r["recipe_id"]))
    i["date"] = pd.to_datetime(i["date"])
    vec, mat = F.build_tfidf(r)
    cf = F.build_cf(i)
    base = BaselineRecommender(r, i, vec, mat, cf)
    ua, ra = A.build_aspect_tables(i)
    M.STATE.clear()
    M.STATE.update({"recipes": r, "inter": i, "baseline": base,
                    "adaptive": AdaptiveRecommender(base, r, i, ua, ra),
                    "ua": ua, "ra": ra, "ing_index": {}})
    conn = sqlite3.connect(TmpIdx)
    conn.execute("CREATE TABLE recipe_names (recipe_id INTEGER, name TEXT)")
    for row in r.itertuples():
        import ast
        try:
            items = ast.literal_eval(row.ingredients) if isinstance(row.ingredients, str) else row.ingredients
        except (ValueError, SyntaxError):
            items = []
        for nm in recipe_name_set([str(x) for x in items], {}):
            conn.execute("INSERT INTO recipe_names VALUES (?,?)", (int(row.recipe_id), nm))
    conn.execute("CREATE INDEX idx_rn_name ON recipe_names(name)")
    conn.commit()
    conn.close()
    cookmod._NAME_DB = Path(TmpIdx)


_state()
c = TestClient(M.app)


def _mkuser(email):
    r = c.post("/api/auth/register", json={"name": "C", "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_coverage_math():
    m, t, ratio, miss = coverage(["onion", "salt"], ["onion", "salt", "chicken"])
    assert ratio == 2 / 3 and miss == {"chicken"}
    assert coverage([], [])[2] == 0.0


def test_cook_flow():
    h = _mkuser("cook@x.com")
    r0 = c.get("/api/cook/matches", headers=h).json()
    assert r0["pantry_empty"] is True
    c.post("/api/pantry/items", headers=h, json={"label": "oats"})
    c.post("/api/pantry/items", headers=h, json={"label": "milk"})
    c.post("/api/pantry/items", headers=h, json={"label": "honey"})
    m = c.get("/api/cook/matches?min_coverage=0.2", headers=h).json()
    assert m["pantry_empty"] is False and len(m["matches"]) > 0
    assert all(x["coverage"] >= 0.2 for x in m["matches"])
    top = m["matches"][0]
    miss = c.get(f"/api/cook/missing/{top['recipe_id']}", headers=h).json()
    assert "missing" in miss
    sh = c.post(f"/api/cook/missing-to-shopping/{top['recipe_id']}", headers=h).json()
    assert sh["added"] == len(miss["missing"])
    assert c.get("/api/cook/matches").status_code == 401
