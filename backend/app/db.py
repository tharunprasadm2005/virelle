"""Virelle application database (SQLite). Separate from Food.com research data.

Entities: users, user_preferences, user_recipe_interactions, meal_plans,
meal_plan_items, shopping_items. Recipes themselves stay in the processed
Food.com dataset (single source of truth, no duplication).
"""
import os
import sqlite3
from pathlib import Path

from src import config

DB_PATH = Path(os.getenv("TASTEFLOW_DB", str(config.PROJECT_ROOT / "tasteflow.db")))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    linked_foodcom_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    diet TEXT DEFAULT '',
    cuisines TEXT DEFAULT '[]',
    priorities TEXT DEFAULT '[]',
    avoid_ingredients TEXT DEFAULT '[]',
    max_minutes INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS user_recipe_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL,
    interaction_type TEXT NOT NULL CHECK(interaction_type IN ('LIKE','DISLIKE','SAVE','UNSAVE','COOKED','RATED','REVIEW')),
    rating INTEGER CHECK(rating IS NULL OR (rating >= 1 AND rating <= 5)),
    review_text TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_inter_user ON user_recipe_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_inter_recipe ON user_recipe_interactions(recipe_id);
CREATE TABLE IF NOT EXISTS meal_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, week_start)
);
CREATE TABLE IF NOT EXISTS meal_plan_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES meal_plans(id) ON DELETE CASCADE,
    day TEXT NOT NULL,
    slot TEXT NOT NULL CHECK(slot IN ('breakfast','lunch','dinner')),
    recipe_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(plan_id, day, slot)
);
CREATE TABLE IF NOT EXISTS shopping_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    category TEXT DEFAULT 'other',
    quantity TEXT DEFAULT '',
    checked INTEGER NOT NULL DEFAULT 0,
    recipe_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_shop_user ON shopping_items(user_id);
"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_app_db():
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def fetch_one(query, params=()):
    conn = connect()
    try:
        return conn.execute(query, params).fetchone()
    finally:
        conn.close()


def fetch_all(query, params=()):
    conn = connect()
    try:
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def execute(query, params=()):
    conn = connect()
    try:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
