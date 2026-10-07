"""Manual QA helper: exercises every page's API surface against REAL data.

Run:  python scripts/qa_check.py
Requires: processed data + trained models (normal pipeline). Creates a
temporary QA user and deletes it afterwards. Prints PASS/FAIL per page.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import backend.app.main as M

PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name, extra)


def main():
    M._load_state()
    from backend.app import db as appdb
    from backend.app import migrations as appmig
    appmig.migrate()
    c = TestClient(M.app, raise_server_exceptions=False)
    r = c.post("/api/auth/register", json={"name": "QA", "email": "qa.check@example.com", "password": "secret123"})
    check("auth/register", r.status_code == 200)
    tok = r.json()["token"]
    H = {"Authorization": "Bearer " + tok}
    check("auth/me", c.get("/api/auth/me", headers=H).status_code == 200)
    p = c.put("/api/preferences", headers=H, json={"diet": "vegetarian", "cuisines": ["indian"],
        "priorities": ["quick", "healthy"], "avoid_ingredients": ["peanuts"], "max_minutes": 30})
    check("onboarding/preferences", p.status_code == 200 and p.json()["cuisines"] == ["indian"])
    h = c.get("/api/home", headers=H).json()
    check("home/cold-start", h["stage"]["stage"] == "getting_to_know" and len(h["recommended"]) > 0,
          f"({len(h['recommended'])} recs)")
    s = c.get("/api/recipes/search?q=paneer&limit=5", headers=H).json()
    check("discover/search-paneer", len(s["results"]) > 0, f"top={s['results'][0]['name'][:40]}")
    f = c.get("/api/recipes/search?q=curry&limit=5&diet=vegetarian", headers=H).json()
    check("discover/veg-filter", len(f["results"]) > 0)
    rid = s["results"][0]["recipe_id"]
    d = c.get(f"/api/recipes/{rid}", headers=H).json()
    check("recipe/detail", d.get("ingredients") and d.get("diet_estimate"), f"ing={len(d.get('ingredients', []))}")
    for kind in ["LIKE", "SAVE", "COOKED"]:
        c.post(f"/api/interactions/{rid}", headers=H, json={"interaction_type": kind})
    c.post(f"/api/interactions/{rid}", headers=H, json={"interaction_type": "RATED", "rating": 5})
    c.post(f"/api/interactions/{rid}", headers=H, json={"interaction_type": "REVIEW", "review_text": "QA: quick and tasty"})
    h2 = c.get("/api/home", headers=H).json()
    check("home/personalized-after-actions", h2["stage"]["stage"] == "personalized")
    for lbl in ["paneer", "tomato", "2 onions"]:
        c.post("/api/pantry/items", headers=H, json={"label": lbl})
    check("pantry/add", len(c.get("/api/pantry", headers=H).json()["items"]) == 3)
    m = c.get("/api/cook/matches?min_coverage=0.2&limit=5", headers=H).json()
    check("cook/matches", not m["pantry_empty"] and len(m["matches"]) > 0,
          f"top cov={m['matches'][0]['coverage']}" if m["matches"] else "")
    if m["matches"]:
        mid = m["matches"][0]["recipe_id"]
        check("cook/missing", "missing" in c.get(f"/api/cook/missing/{mid}", headers=H).json())
        check("cook/missing-to-shopping", c.post(f"/api/cook/missing-to-shopping/{mid}", headers=H).status_code == 200)
    mp = c.post("/api/meal-plans/generate?week_start=2026-10-05", headers=H).json()
    check("meals/generate", mp["filled"] > 0, f"filled={mp['filled']}")
    check("shopping/from-recipe", c.post(f"/api/shopping-list/from-recipe/{rid}", headers=H).status_code == 200)
    mg = c.post("/api/shopping-list/merge-duplicates", headers=H).json()
    check("shopping/merge", "merged" in mg)
    t = c.get("/api/taste", headers=H).json()
    check("taste/profile", t["has_history"] is True)
    check("taste/evolution", c.get("/api/taste/evolution", headers=H).json()["has_history"] is True)
    col = c.post("/api/collections", headers=H, json={"name": "QA List"}).json()
    check("collections/create+add",
          c.post(f"/api/collections/{col['id']}/items", headers=H, json={"recipe_id": rid}).status_code == 200)
    check("research/summary", len(c.get("/api/research/summary", headers=H).json().get("ablation", [])) > 0)
    uid = c.get("/api/auth/me", headers=H).json()["id"]
    for tbn, coln in (("recommendation_events", "user_id"), ("collection_items", "collection_id"),
                      ("collections", "user_id"), ("pantry_items", "user_id"), ("shopping_items", "user_id"),
                      ("user_recipe_interactions", "user_id"), ("meal_plan_items", "plan_id"),
                      ("meal_plans", "user_id"), ("users", "email")):
        try:
            appdb.execute(f"DELETE FROM {tbn} WHERE {coln}=?",
                          ("qa.check@example.com",) if coln == "email" else (uid,) if tbn != "collection_items" else (col["id"],))
        except Exception:
            pass
    appdb.execute("DELETE FROM collection_items WHERE collection_id=?", (col["id"],))
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed" + (f": {FAIL}" if FAIL else ""))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
