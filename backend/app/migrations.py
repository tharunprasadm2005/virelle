"""Ordered SQLite schema migrations. No ORM by decision (see
docs/architecture/current.md): single-node scale, raw sqlite3 throughout.

Convention: append (version, description, sql). Applied at startup via migrate().
v1 = the original Phase-0 schema (already applied by init_app_db on existing DBs;
recorded without re-running destructive statements — all statements are
CREATE TABLE/INDEX IF NOT EXISTS, so re-running is safe).
"""
from backend.app import db as appdb

V1_SCHEMA_SQL = None  # filled lazily from db.SCHEMA to avoid duplication


def _v1_sql():
    from backend.app.db import SCHEMA
    return SCHEMA


MIGRATIONS = [(1, "phase-0 baseline schema (users, preferences, interactions, meal plans, shopping)", _v1_sql),
              (2, "phase-3 pantry items (user-owned, availability flag, optional expiry)",
               """CREATE TABLE IF NOT EXISTS pantry_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    normalized_name TEXT NOT NULL DEFAULT '',
    quantity TEXT DEFAULT '',
    unit TEXT DEFAULT '',
    category TEXT DEFAULT 'other',
    expiry TEXT,
    available INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS              idx_pantry_user ON pantry_items(user_id);"""),
              (3, "phase-9 nutrition goals preference",
               "ALTER TABLE user_preferences ADD COLUMN nutrition_goals TEXT DEFAULT '[]';"),
              (4, "phase-10 user-imported recipes (attributed, user-owned)",
               """CREATE TABLE IF NOT EXISTS imported_recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    ingredients TEXT NOT NULL DEFAULT '[]',
    instructions TEXT NOT NULL DEFAULT '[]',
    servings TEXT DEFAULT '',
    total_minutes INTEGER,
    image_url TEXT DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    source_name TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_imported_user ON imported_recipes(user_id);"""),
              (5, "phase-11 collections/cookbooks (user-owned, recipe refs)",
               """CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, name)
);
CREATE TABLE IF NOT EXISTS collection_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'foodcom' CHECK(source IN ('foodcom','imported')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(collection_id, recipe_id, source)
);
CREATE INDEX IF NOT EXISTS idx_coll_user ON collections(user_id);
CREATE INDEX IF NOT EXISTS idx_collitem_coll ON collection_items(collection_id);"""),
              (6, "phase-13 recommendation events (impressions/opens; skips derived, never stored as fake)",
               """CREATE TABLE IF NOT EXISTS recommendation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('SHOWN','OPENED')),
    context TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_evt_user ON recommendation_events(user_id);
CREATE INDEX IF NOT EXISTS idx_evt_recipe ON recommendation_events(recipe_id);"""),
              (7, "brand migration: demo account email tasteflow -> virelle (data, not schema)",
               "UPDATE users SET email='demo@virelle.app' WHERE email='demo@tasteflow.app';")]


def migrate():
    conn = appdb.connect()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations "
                     "(version INTEGER PRIMARY KEY, description TEXT, applied_at TEXT NOT NULL DEFAULT (datetime('now')))")
        applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        for version, desc, sql_fn in sorted(MIGRATIONS):
            if version in applied:
                continue
            sql = sql_fn() if callable(sql_fn) else sql_fn
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations (version, description) VALUES (?,?)", (version, desc))
            conn.commit()
    finally:
        conn.close()
