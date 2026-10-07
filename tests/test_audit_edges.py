"""Phase 33: edge-case audit across every router (no behavior faked)."""
import os
import pandas as pd
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

TmpDB = os.path.join(os.path.dirname(__file__), "test_edge_tmp.db")
if os.path.exists(TmpDB):
    os.remove(TmpDB)

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
import backend.app.main as M


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


_state()
c = TestClient(M.app)


def _tok(email):
    r = c.post("/api/auth/register", json={"name": "E", "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_auth_edges():
    assert c.post("/api/auth/register", json={"name": "", "email": "bad", "password": "x"}).status_code in (401, 422)
    assert c.post("/api/auth/register", json={"name": "E", "email": "e@x.com"}).status_code == 422
    assert c.post("/api/auth/login", json={"email": "nope@x.com", "password": "secret123"}).status_code == 401
    import jwt
    from backend.app import auth as A_
    expired = jwt.encode({"sub": "1", "exp": datetime.utcnow() - timedelta(seconds=1)}, A_.SECRET, algorithm=A_.ALGO)
    assert c.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert c.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_recipe_edges():
    h = _tok("re@x.com")
    assert c.get("/api/recipes?limit=2&offset=1", headers=h).json()[0]["recipe_id"] == 2
    assert c.get("/api/recipes?limit=2&offset=9999", headers=h).json() == []
    assert c.get("/api/recipes?limit=0", headers=h).status_code == 422
    assert c.get("/api/recipes/abc", headers=h).status_code == 422
    r = c.get("/api/recipes/search?q=&limit=5", headers=h)
    assert r.status_code == 422  # min_length=1 enforced


def test_interaction_edges():
    h = _tok("ie@x.com")
    assert c.post("/api/interactions/1", headers=h, json={"interaction_type": "RATED", "rating": 9}).status_code == 422
    assert c.post("/api/interactions/-5", headers=h, json={"interaction_type": "LIKE"}).status_code == 404
    assert c.post("/api/interactions/1", json={"interaction_type": "LIKE"}).status_code == 401


def test_mealprep_edges():
    h = _tok("me@x.com")
    assert c.put("/api/meal-plans/slot?week_start=x", headers=h, json={"day": "xx", "slot": "lunch"}).status_code == 422
    assert c.put("/api/meal-plans/slot?week_start=x", headers=h, json={"day": "monday", "slot": "brunch"}).status_code == 422
    g = c.get("/api/meal-plans?week_start=2099-01-05", headers=h).json()
    assert all(v is None for d in g["grid"].values() for v in d.values())


def test_collections_imports_edges():
    h = _tok("ci@x.com")
    assert c.post("/api/collections", headers=h, json={"name": ""}).status_code == 422
    assert c.get("/api/collections/99999", headers=h).status_code == 404
    assert c.delete("/api/imports/99999", headers=h).status_code == 404
    assert c.post("/api/imports", headers=h, json={"url": "not a url at all!!!$$$%%%"}).status_code in (404, 422)


def test_pantry_cook_edges():
    h = _tok("pc@x.com")
    assert c.put("/api/pantry/items/99999", headers=h, json={"quantity": "1"}).status_code == 404
    assert c.get("/api/cook/missing/999999", headers=h).json()["missing"] == []
    assert c.post("/api/shopping-list/items", headers=h, json={"label": ""}).status_code == 422
