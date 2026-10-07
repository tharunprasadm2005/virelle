"""Phase 10 tests: SSRF guard + offline parse + import endpoints."""
import json
import pytest

from src.recipes import importer as IMP

HTML = """<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Recipe","name":"Test Soup",
 "recipeIngredient":["2 cups water","1 onion"],
 "recipeInstructions":[{"@type":"HowToStep","text":"Boil water."},{"@type":"HowToStep","text":"Add onion."}],
 "recipeYield":"4 servings","totalTime":"PT30M","image":"https://example.com/soup.jpg"}
</script></head><body></body></html>"""


def test_ssrf_guard_no_network():
    for bad in ["http://127.0.0.1/x", "http://10.0.0.5/", "http://192.168.1.1/a",
                "http://169.254.169.254/latest", "ftp://example.com/x", "not a url",
                "http://localhost:8000/api/health", "http://0.0.0.0/", "http://[::1]/x",
                "http://[fe80::1]/x", "http://2130706433/", "http://0177.0.0.1/"]:
        try:
            IMP.assert_safe_url(bad)
            raise AssertionError(f"should refuse {bad}")
        except ValueError:
            pass


def test_offline_parse_fixture():
    from recipe_scrapers import scrape_html
    s = scrape_html(HTML, "https://example.com/test-soup", wild_mode=True)
    assert "Soup" in s.title()
    assert len(s.ingredients()) >= 2


def test_import_endpoints_offline(monkeypatch):
    import backend.app.main as M
    from fastapi.testclient import TestClient
    from backend.app import db as appdb
    from pathlib import Path
    import os
    tmp = os.path.join(os.path.dirname(__file__), "test_import_tmp.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    appdb.DB_PATH = Path(tmp)
    from backend.app import migrations as appmig
    appmig.migrate()

    def fake_fetch(url):
        IMP.assert_safe_url(url)  # real guard still enforced (no network in test)
        assert url.startswith("https://example.com/")
        return {"title": "Test Soup", "ingredients": ["2 cups water"], "instructions": ["Boil."],
                "servings": "4", "total_time": 30, "image_url": "", "source_url": url, "source_name": "example.com"}

    monkeypatch.setattr(IMP, "fetch_and_parse", fake_fetch)
    # also patch the router's reference (it imported the module, attribute lookup is live)
    import backend.app.api.imports as impmod
    assert impmod.IMP is IMP
    c = TestClient(M.app)
    # minimal STATE for main import (router needs STATE only on data routes)
    tok = c.post("/api/auth/register", json={"name": "I", "email": "imp@x.com", "password": "secret123"}).json()["token"]
    h = {"Authorization": "Bearer " + tok}
    assert c.post("/api/imports", headers=h, json={"url": "http://10.0.0.1/evil"}).status_code == 422
    r = c.post("/api/imports", headers=h, json={"url": "https://example.com/test-soup"}).json()
    assert r["title"] == "Test Soup" and r["imported"] is True
    assert len(c.get("/api/imports", headers=h).json()["imports"]) == 1
    assert c.delete(f"/api/imports/{r['id']}", headers=h).json() == {"ok": True}
    assert c.get("/api/imports", headers=h).json() == {"imports": []}
    if os.path.exists(tmp):
        os.remove(tmp)
