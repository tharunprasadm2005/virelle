"""Phase 3 tests: pantry CRUD, ownership, validation. Isolated temp DB."""
import os
import pandas as pd
from fastapi.testclient import TestClient

TmpDB = os.path.join(os.path.dirname(__file__), "test_pantry_tmp.db")
if os.path.exists(TmpDB):
    os.remove(TmpDB)
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


def _mkuser(email):
    r = c.post("/api/auth/register", json={"name": "N", "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_pantry_crud():
    h = _mkuser("pan@x.com")
    assert c.get("/api/pantry", headers=h).json() == {"items": []}
    it = c.post("/api/pantry/items", headers=h, json={"label": "2 onions"}).json()["items"][0]
    assert it["normalized_name"] == "onion" and it["available"] == 1
    multi = c.post("/api/pantry/items", headers=h, json={"label": "paneer, tomato"}).json()["items"]
    assert sorted(i["normalized_name"] for i in multi) == ["paneer", "tomato"]
    typo = c.post("/api/pantry/items", headers=h, json={"label": "panner"}).json()["items"][0]
    assert typo["normalized_name"] == "paneer" and typo["label"] == "panner"
    assert c.post("/api/pantry/items", headers=h, json={"label": ""}).status_code == 422
    assert c.post("/api/pantry/items", headers=h, json={"label": "milk", "expiry": "not-a-date"}).status_code == 422
    ed = c.put(f"/api/pantry/items/{it['id']}", headers=h, json={"quantity": "3", "expiry": "2026-12-31"}).json()
    assert ed["quantity"] == "3" and ed["expiry"] == "2026-12-31"
    tg = c.patch(f"/api/pantry/items/{it['id']}/availability", headers=h).json()
    assert tg["available"] == 0
    assert c.delete(f"/api/pantry/items/{it['id']}", headers=h).json() == {"ok": True}
    for left in c.get("/api/pantry", headers=h).json()["items"]:
        assert c.delete(f"/api/pantry/items/{left['id']}", headers=h).json() == {"ok": True}
    assert c.get("/api/pantry", headers=h).json() == {"items": []}


def test_pantry_ownership():
    a = _mkuser("pa@x.com")
    b = _mkuser("pb@x.com")
    it = c.post("/api/pantry/items", headers=a, json={"label": "paneer"}).json()["items"][0]
    assert c.get("/api/pantry", headers=b).json() == {"items": []}
    assert c.put(f"/api/pantry/items/{it['id']}", headers=b, json={"quantity": "9"}).status_code == 404
    assert c.patch(f"/api/pantry/items/{it['id']}/availability", headers=b).status_code == 404
    assert c.delete(f"/api/pantry/items/{it['id']}", headers=b).status_code == 404
    assert c.get("/api/pantry").status_code == 401
