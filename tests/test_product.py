"""Product tests: auth, prefs, search, interactions, home, taste, meals, shopping.
Uses an isolated temp app DB + the tiny TEST FIXTURE engine state (never real data)."""
import os
import pandas as pd
from fastapi.testclient import TestClient

TmpDB = os.path.join(os.path.dirname(__file__), "test_tasteflow_tmp.db")
if os.path.exists(TmpDB):
    os.remove(TmpDB)

from backend.app import db as appdb
from pathlib import Path
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
                    "ua": ua, "ra": ra})


_state()
c = TestClient(M.app)


def _reg(name="Tharun", email="t@t.com", pw="secret123", **kw):
    r = c.post("/api/auth/register", json={"name": name, "email": email, "password": pw, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_register_login_me():
    u = _reg()
    tok = u["token"]
    assert c.get("/api/auth/me", headers=_h(tok)).json()["name"] == "Tharun"
    assert c.post("/api/auth/register", json={"name": "x", "email": "t@t.com", "password": "secret123"}).status_code == 409
    assert c.post("/api/auth/login", json={"email": "t@t.com", "password": "wrong"}).status_code == 401
    assert c.get("/api/auth/me").status_code == 401
    assert c.get("/api/auth/me", headers=_h("bad")).status_code == 401
    assert c.post("/api/auth/refresh", headers=_h(tok)).status_code == 200
    assert c.post("/api/auth/refresh").status_code == 401
    import os
    import backend.app.main as _M
    os.environ["RATE_LIMIT_AUTH_PER_MIN"] = "2"
    _M._rate.clear()
    assert c.post("/api/auth/login", json={"email": "t@t.com", "password": "wrong"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "t@t.com", "password": "wrong"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "t@t.com", "password": "wrong"}).status_code == 429
    del os.environ["RATE_LIMIT_AUTH_PER_MIN"]
    _M._rate.clear()


def test_prefs_roundtrip_and_validation():
    tok = _reg("P", "p@p.com")["token"]
    r = c.put("/api/preferences", headers=_h(tok),
              json={"diet": "vegetarian", "cuisines": ["indian"], "priorities": ["quick"],
                    "avoid_ingredients": ["peanuts"], "max_minutes": 30})
    assert r.status_code == 200, r.text
    assert r.json()["cuisines"] == ["indian"] and r.json()["max_minutes"] == 30
    assert c.put("/api/preferences", headers=_h(tok), json={"diet": "carnivore"}).status_code == 422
    g = c.put("/api/preferences", headers=_h(tok), json={"nutrition_goals": ["high protein", "bogus"]})
    assert g.status_code == 200 and g.json()["nutrition_goals"] == ["high protein"]
    h = c.get("/api/home", headers=_h(tok)).json()
    assert "nutrition_goals" in h
    assert c.get("/api/recipes/search?q=soup&min_protein=10&max_calories=500", headers=_h(tok)).status_code == 200


def test_search_and_catalog():
    tok = _reg("S", "s@s.com")["token"]
    r = c.get("/api/recipes/search?q=healthy&limit=5", headers=_h(tok))
    assert r.status_code == 200 and len(r.json()["results"]) > 0
    assert "image_url" in r.json()["results"][0]
    assert r.json()["mode"] == "hybrid" and "weights" in r.json()
    rk = c.get("/api/recipes/search?q=healthy&limit=5&mode=keyword", headers=_h(tok))
    assert rk.status_code == 200 and len(rk.json()["results"]) > 0
    d = c.get("/api/discover", headers=_h(tok))
    assert d.status_code == 200 and len(d.json()["sections"]) > 0
    assert c.get("/api/recipes/1", headers=_h(tok)).status_code == 200
    assert c.get("/api/recipes/9999", headers=_h(tok)).status_code == 404


def test_interactions_favorites_home_taste():
    tok = _reg("H", "h@h.com")["token"]
    h = _h(tok)
    home0 = c.get("/api/home", headers=h).json()
    assert home0["stage"]["stage"] == "getting_to_know"
    assert c.post("/api/interactions/1", headers=h, json={"interaction_type": "LIKE"}).status_code == 200
    assert c.post("/api/interactions/4", headers=h, json={"interaction_type": "SAVE"}).status_code == 200
    assert c.post("/api/interactions/5", headers=h, json={"interaction_type": "DISLIKE"}).status_code == 200
    assert c.post("/api/interactions/2", headers=h, json={"interaction_type": "RATED", "rating": 5}).status_code == 200
    assert c.post("/api/interactions/2", headers=h, json={"interaction_type": "RATED"}).status_code == 422
    assert c.post("/api/interactions/1", headers=h, json={"interaction_type": "HUG"}).status_code == 422
    assert c.post("/api/interactions/9999", headers=h, json={"interaction_type": "LIKE"}).status_code == 404
    assert c.post("/api/interactions/3", headers=h, json={"interaction_type": "COOKED"}).status_code == 200
    mine = c.get("/api/interactions/mine", headers=h).json()["interactions"]
    assert any(m["interaction_type"] == "COOKED" and m["recipe_id"] == 3 for m in mine)
    favs = c.get("/api/favorites", headers=h).json()["favorites"]
    assert any(f["recipe_id"] == 4 for f in favs)
    home1 = c.get("/api/home", headers=h).json()
    assert home1["stage"]["stage"] == "personalized"
    assert len(home1["recommended"]) > 0 and "why" in home1["recommended"][0]
    t = c.get("/api/taste", headers=h).json()
    assert t["has_history"] is True and "aspects" in t
    ev = c.get("/api/taste/evolution", headers=h).json()
    assert ev["has_history"] is True and "earlier_recipes" in ev
    assert c.post("/api/events", headers=h, json={"recipe_id": 1, "event_type": "OPENED"}).json() == {"ok": True}
    assert c.post("/api/events/shown-batch", headers=h, json={"recipe_ids": [1, 2], "context": "home"}).json()["recorded"] == 2
    assert c.post("/api/events", headers=h, json={"recipe_id": 1, "event_type": "IGNORED"}).status_code == 422
    assert c.post("/api/events/shown-batch", headers=h, json={"recipe_ids": []}).status_code == 422
    hi = c.get("/api/home?intent=quick+soup", headers=h).json()
    assert hi["stage"]["stage"] == "personalized" and len(hi["recommended"]) > 0


def test_meals_and_shopping_and_authz():
    a = _reg("A", "a@a.com")["token"]
    b = _reg("B", "b@b.com")["token"]
    wk = "2026-10-05"
    g = c.post(f"/api/meal-plans/generate?week_start={wk}", headers=_h(a)).json()
    assert g["filled"] > 0
    s = c.put(f"/api/meal-plans/slot?week_start={wk}", headers=_h(a),
              json={"day": "monday", "slot": "lunch", "recipe_id": 1})
    assert s.status_code == 200
    assert c.put(f"/api/meal-plans/slot?week_start={wk}", headers=_h(a),
                 json={"day": "funday", "slot": "lunch", "recipe_id": 1}).status_code == 422
    it = c.post("/api/shopping-list/items", headers=_h(a), json={"label": "Paneer", "quantity": "500 g"}).json()["items"][0]
    assert it["category"] == "dairy"
    assert c.patch(f"/api/shopping-list/items/{it['id']}", headers=_h(b)).status_code == 404
    assert c.patch(f"/api/shopping-list/items/{it['id']}", headers=_h(a)).status_code == 200
    fr = c.post("/api/shopping-list/from-recipe/1", headers=_h(a))
    assert fr.status_code == 200 and fr.json()["added"] >= 1
    assert c.post("/api/shopping-list/clear-completed", headers=_h(a)).status_code == 200
    m1 = c.post("/api/shopping-list/items", headers=_h(a), json={"label": "Onion", "quantity": "2"}).json()
    m2 = c.post("/api/shopping-list/items", headers=_h(a), json={"label": "1 onion", "quantity": "1"}).json()
    mg = c.post("/api/shopping-list/merge-duplicates", headers=_h(a)).json()
    assert mg["merged"] == 1
    left = [i for i in c.get("/api/shopping-list", headers=_h(a)).json()["items"] if "onion" in i["label"]]
    assert len(left) == 1 and left[0]["quantity"].startswith("3")
    assert c.post("/api/shopping-list/from-pantry/9999", headers=_h(a)).status_code == 404
    assert c.delete(f"/api/shopping-list/items/{it['id']}", headers=_h(a)).status_code in (200, 404)


def test_research_and_profile():
    tok = _reg("R", "r@r.com")["token"]
    s = c.get("/api/research/summary", headers=_h(tok))
    assert s.status_code == 200 and "ablation" in s.json()
    p = c.get("/api/profile", headers=_h(tok)).json()
    assert p["email"] == "r@r.com"
    assert c.put("/api/profile", headers=_h(tok), json={"name": "R2"}).json()["name"] == "R2"
    assert c.post("/api/profile/password", headers=_h(tok),
                  json={"current_password": "nope", "new_password": "newsecret1"}).status_code == 403
    assert c.post("/api/profile/password", headers=_h(tok),
                  json={"current_password": "secret123", "new_password": "newsecret1"}).status_code == 200
    assert c.post("/api/auth/login", json={"email": "r@r.com", "password": "newsecret1"}).status_code == 200


def _tok(email, name="C"):
    r = c.post("/api/auth/register", json={"name": name, "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_image_policy_suppresses_dead():
    from backend.app.api import cards as cardsmod
    cardsmod.set_image_policy(dead={1}, live={2})
    try:
        r = P.preprocess_recipes(tiny_recipes())
        row2 = r[r["recipe_id"] == 2].iloc[0].to_dict()
        row2["image_url"] = "http://x/y.jpg"
        row1 = r[r["recipe_id"] == 1].iloc[0].to_dict()
        row1["image_url"] = "http://x/dead.jpg"
        assert cardsmod.card(row2, 2)["image_url"] == "http://x/y.jpg"
        assert cardsmod.card(row1, 1)["image_url"] is None
        assert cardsmod.image_ok(1) is False and cardsmod.image_ok(2) is True and cardsmod.image_ok(9) is None
    finally:
        cardsmod.set_image_policy(set(), set())


def test_collections():
    a = _tok("ca@x.com")
    b = _tok("cb@x.com")
    col = c.post("/api/collections", headers=a, json={"name": "Weeknight"}).json()
    cid = col["id"]
    assert c.post("/api/collections", headers=a, json={"name": "Weeknight"}).status_code == 409
    assert c.post(f"/api/collections/{cid}/items", headers=a, json={"recipe_id": 1}).status_code == 200
    assert c.post(f"/api/collections/{cid}/items", headers=a, json={"recipe_id": 1}).status_code == 409
    assert c.post(f"/api/collections/{cid}/items", headers=a, json={"recipe_id": 9999}).status_code == 404
    assert c.get(f"/api/collections/{cid}", headers=b).status_code == 404
    got = c.get(f"/api/collections/{cid}", headers=a).json()
    assert len(got["recipes"]) == 1 and got["recipes"][0]["recipe_id"] == 1
    rn = c.put(f"/api/collections/{cid}", headers=a, json={"name": "Fast"}).json()
    assert rn["name"] == "Fast"
    assert c.delete(f"/api/collections/{cid}/items?recipe_id=1&source=foodcom", headers=a).json() == {"ok": True}
    assert c.get(f"/api/collections/{cid}", headers=a).json()["recipes"] == []
    assert c.delete(f"/api/collections/{cid}", headers=a).json() == {"ok": True}
    assert c.get("/api/collections", headers=a).json() == {"collections": []}
