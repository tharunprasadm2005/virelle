"""Phase 43: critical user journeys on fixture data (no hardcoded real ids)."""
import os
import pandas as pd
from fastapi.testclient import TestClient

TmpDB = os.path.join(os.path.dirname(__file__), "test_journey_tmp.db")
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


def _reg(email, name="J"):
    r = c.post("/api/auth/register", json={"name": name, "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_journey_new_user_full_loop():
    h = _reg("j1@x.com")
    c.put("/api/preferences", headers=h, json={"diet": "", "cuisines": [], "priorities": ["quick"]})
    assert c.get("/api/home", headers=h).json()["stage"]["stage"] == "getting_to_know"
    rid = c.get("/api/recipes/search?q=healthy&limit=3", headers=h).json()["results"][0]["recipe_id"]
    assert c.get(f"/api/recipes/{rid}", headers=h).status_code == 200
    for kind in ["SAVE", "LIKE", "COOKED"]:
        assert c.post(f"/api/interactions/{rid}", headers=h, json={"interaction_type": kind}).status_code == 200
    assert c.post(f"/api/interactions/{rid}", headers=h, json={"interaction_type": "RATED", "rating": 4}).status_code == 200
    assert c.get("/api/home", headers=h).json()["stage"]["stage"] == "personalized"
    assert c.get("/api/taste", headers=h).json()["has_history"] is True
    wk = "2026-11-02"
    assert c.post(f"/api/meal-plans/generate?week_start={wk}", headers=h).json()["filled"] >= 0
    assert c.post(f"/api/shopping-list/from-recipe/{rid}", headers=h).status_code == 200
    assert c.post("/api/shopping-list/merge-duplicates", headers=h).status_code == 200


def test_journey_pantry_cook():
    h = _reg("j2@x.com")
    c.post("/api/pantry/items", headers=h, json={"label": "oats"})
    c.post("/api/pantry/items", headers=h, json={"label": "milk"})
    m = c.get("/api/cook/matches?min_coverage=0.2", headers=h).json()
    assert m["pantry_empty"] is False
    if m["matches"]:
        top = m["matches"][0]["recipe_id"]
        miss = c.get(f"/api/cook/missing/{top}", headers=h).json()
        assert c.post(f"/api/cook/missing-to-shopping/{top}", headers=h).json()["added"] == len(miss["missing"])


def test_journey_login_personalized_and_cold():
    h = _reg("j3@x.com")
    c.put("/api/preferences", headers=h, json={"cuisines": ["indian"]})
    c.post("/api/interactions/1", headers=h, json={"interaction_type": "LIKE"})
    c.post("/api/interactions/1", headers=h, json={"interaction_type": "LIKE"})
    assert c.get("/api/home", headers=h).json()["stage"]["stage"] == "personalized"
    h2 = _reg("j4@x.com")
    assert c.get("/api/home", headers=h2).json()["stage"]["stage"] == "getting_to_know"
