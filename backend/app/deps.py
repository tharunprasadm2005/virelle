"""Shared application state (single owner) + access guard.

Routers must import STATE from HERE, never from backend.app.main
(which imports the routers — the old cycle). main.py re-exports the same
object so existing tests touching M.STATE keep working.
"""
from fastapi import HTTPException

from src import config

STATE: dict = {}


def require_state() -> dict:
    if "adaptive" not in STATE:
        raise HTTPException(503, config.MISSING_DATA_MSG + " Then run: preprocess -> build_features -> train.")
    return STATE


def rmap(state: dict):
    """Recipes indexed by recipe_id, built once (Phase 38 hot-path cache)."""
    m = state.get("rmap")
    if m is None:
        m = state["recipes"].set_index("recipe_id")
        state["rmap"] = m
    return m


def rname(state: dict):
    """recipe_id -> name dict, built once."""
    m = state.get("rname")
    if m is None:
        m = rmap(state)["name"].to_dict()
        state["rname"] = m
    return m


def recipe_ids(state: dict):
    ids = state.get("recipe_ids")
    if ids is None:
        ids = set(state["recipes"]["recipe_id"].tolist())
        state["recipe_ids"] = ids
    return ids
