"""API tests with tiny TEST FIXTURE state (not project data)."""
import pandas as pd
from fastapi.testclient import TestClient
from src.data import preprocess as P
from src.data import features as F
from src.recommender.baseline import BaselineRecommender
from src.recommender.hybrid import AdaptiveRecommender
from src.recommender import aspect_model as A
from tests.fixtures import tiny_recipes, tiny_interactions
import backend.app.main as M


def _client():
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
    return TestClient(M.app)


def test_recipe_endpoints():
    c = _client()
    assert c.get("/api/recipes").status_code == 200
    assert c.get("/api/recipes/1").status_code == 200
    assert c.get("/api/recipes/9999").status_code == 404


def test_recommendation_and_preference_endpoints():
    c = _client()
    r = c.get("/api/recommendations/2?k=3&mode=full")
    assert r.status_code == 200
    assert len(r.json()["recommendations"]) > 0
    assert c.get("/api/recommendations/9999?k=2").json()["cold_start"] is True
    assert "shift" in c.get("/api/preferences/1").json()
    assert "aspects" in c.get("/api/preferences/1/aspects").json()
    assert c.get("/api/health").status_code == 200


def test_demo_users_and_evolution_names():
    c = _client()
    d = c.get("/api/demo_users?min_interactions=2&min_reviews=1&limit=5")
    assert d.status_code == 200
    body = d.json()
    assert "users" in body and "default_user_id" in body
    if body["users"]:
        u = body["users"][0]
        assert {"user_id", "n_interactions", "n_reviews", "shift"} <= set(u)
    ev = c.get("/api/preferences/2/evolution")
    assert ev.status_code == 200
    assert "earlier_recipes" in ev.json() and "recent_recipes" in ev.json()
