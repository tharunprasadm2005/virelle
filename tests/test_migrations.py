"""Phase 35: migration correctness (fresh DB, ordering, idempotency)."""
import os
import sqlite3
from pathlib import Path

TmpDB = os.path.join(os.path.dirname(__file__), "test_mig_tmp.db")
if os.path.exists(TmpDB):
    os.remove(TmpDB)

from backend.app import db as appdb
appdb.DB_PATH = Path(TmpDB)
from backend.app import migrations as appmig

import pytest


@pytest.fixture(autouse=True)
def _isolated_db():
    from pathlib import Path as _P
    import os as _os
    if _os.path.exists(TmpDB):
        _os.remove(TmpDB)
    appdb.DB_PATH = _P(TmpDB)
    yield
    if _os.path.exists(TmpDB):
        _os.remove(TmpDB)

EXPECTED_TABLES = {"users", "user_preferences", "user_recipe_interactions", "meal_plans",
                   "meal_plan_items", "shopping_items", "pantry_items", "imported_recipes",
                   "collections", "collection_items", "recommendation_events", "schema_migrations"}


def test_fresh_migration():
    appmig.migrate()
    conn = sqlite3.connect(TmpDB)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert EXPECTED_TABLES <= tables
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
    assert versions == sorted(v[0] for v in appmig.MIGRATIONS) == list(range(1, len(appmig.MIGRATIONS) + 1))
    # FKs parse: spot-check one cascade
    fks = list(conn.execute("PRAGMA foreign_key_list(user_recipe_interactions)"))
    assert any(f[2] == "users" for f in fks)
    conn.close()
    if os.path.exists(TmpDB):
        os.remove(TmpDB)


def test_idempotent_rerun():
    appmig.migrate()
    appmig.migrate()  # must not raise (IF NOT EXISTS / version guard)
    conn = sqlite3.connect(TmpDB)
    assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == len(appmig.MIGRATIONS)
    conn.close()
    if os.path.exists(TmpDB):
        os.remove(TmpDB)


def test_v7_demo_email_migration():
    from backend.app import db as appdb
    appmig.migrate()
    conn = sqlite3.connect(TmpDB)
    conn.execute("INSERT INTO users (name, email, password_hash, linked_foodcom_id) VALUES (?,?,?,?)",
                 ("Demo", "demo@tasteflow.app", "x", 269575))
    conn.commit()
    conn.close()
    appmig.migrate()  # v7 must already be recorded -> no-op; simulate fresh-v6 below instead
    # fresh v6 DB then migrate must rename
    if os.path.exists(TmpDB):
        os.remove(TmpDB)
    appmig.migrate()
    conn = sqlite3.connect(TmpDB)
    conn.execute("INSERT INTO users (name, email, password_hash) VALUES (?,?,?)", ("D", "demo@tasteflow.app", "x"))
    conn.commit()
    conn.close()
    # reset recorded versions to simulate pre-v7 DB
    conn = sqlite3.connect(TmpDB)
    conn.execute("DELETE FROM schema_migrations WHERE version=7")
    conn.commit()
    conn.close()
    appmig.migrate()
    conn = sqlite3.connect(TmpDB)
    emails = [r[0] for r in conn.execute("SELECT email FROM users")]
    assert emails == ["demo@virelle.app"]
    conn.close()
    if os.path.exists(TmpDB):
        os.remove(TmpDB)
