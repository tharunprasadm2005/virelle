"""Virelle backend — product API over the preserved adaptive engine.

Research endpoints (/api/recommendations/{id}, /api/preferences/*, /api/demo_users,
/api/dataset/*) are unchanged. Product routers add auth, taste, search, meals,
shopping, and research summary. No ML logic lives in this layer.
"""
import logging
import os
import time
import uuid
from pathlib import Path
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from src import config
from src.recommender.explanations import explain

from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tasteflow")


@asynccontextmanager
async def lifespan(app_: FastAPI):
    _load_state()
    from backend.app import migrations as appmigrations
    appmigrations.migrate()
    import threading
    def _warm():
        try:
            from src.recommender import semantic_search as _sem
            if _sem.available():
                _sem.search("warmup query", k=1)
        except Exception:
            pass
    threading.Thread(target=_warm, daemon=True).start()  # first semantic hit w/o blocking boot
    yield


app = FastAPI(title="Virelle - Recipes that learn your taste", lifespan=lifespan)
from backend.app.deps import STATE, require_state as _require_state  # noqa (re-export: tests use M.STATE)

from backend.app.api import auth as auth_routes
from backend.app.api import profile as profile_routes
from backend.app.api import interactions as inter_routes
from backend.app.api import taste as taste_routes
from backend.app.api import search as search_routes
from backend.app.api import mealplan as meal_routes
from backend.app.api import shopping as shop_routes
from backend.app.api import ingredients as ing_routes
from backend.app.api import pantry as pantry_routes
from backend.app.api import cook as cook_routes
from backend.app.api import imports as imports_routes
from backend.app.api import collections as collections_routes
from backend.app.api import events as events_routes
from backend.app.api import research as research_routes
app.include_router(auth_routes.router)
app.include_router(profile_routes.router)
app.include_router(inter_routes.router)
app.include_router(taste_routes.router)
app.include_router(search_routes.router)
app.include_router(meal_routes.router)
app.include_router(shop_routes.router)
app.include_router(ing_routes.router)
app.include_router(pantry_routes.router)
app.include_router(cook_routes.router)
app.include_router(imports_routes.router)
app.include_router(collections_routes.router)
app.include_router(events_routes.router)


@app.middleware("http")
async def request_log(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    t = time.time()
    try:
        resp = await call_next(request)
        log.info("%s %s %s %.0fms", rid, request.method, request.url.path,
                 (time.time() - t) * 1000)
        resp.headers["X-Request-Id"] = rid
        return resp
    except Exception:
        log.exception("%s %s %s FAILED", rid, request.method, request.url.path)
        return JSONResponse({"detail": "Internal error", "request_id": rid}, status_code=500)


_rate: dict[str, list[float]] = {}


@app.middleware("http")
async def auth_limit(request: Request, call_next):
    # Backstop limiter (real brute-force protection belongs at the reverse
    # proxy). Limit tunable via RATE_LIMIT_AUTH_PER_MIN (default 60/min/IP).
    if request.url.path in ("/api/auth/login", "/api/auth/register"):
        try:
            limit = int(os.getenv("RATE_LIMIT_AUTH_PER_MIN", "60"))
        except ValueError:
            limit = 60
        ip = request.client.host if request.client else "?"
        now = time.time()
        hits = [h for h in _rate.get(ip, []) if now - h < 60]
        if len(hits) >= limit:
            return JSONResponse({"detail": "Too many attempts — try again in a minute."}, status_code=429)
        hits.append(now)
        _rate[ip] = hits
    return await call_next(request)


_cors = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if _cors:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware, allow_origins=_cors, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                       allow_headers=["Authorization", "Content-Type"])
app.include_router(research_routes.router)


def _load_state():
    try:
        STATE["recipes"] = pd.read_csv(config.DATA_PROCESSED_DIR / "recipes_processed.csv")
        STATE["inter"] = pd.read_csv(config.DATA_PROCESSED_DIR / "interactions_processed.csv")
        # hot-path caches (Phase 38): indexed frame + id sets built ONCE
        STATE["rmap"] = STATE["recipes"].set_index("recipe_id")
        STATE["recipe_ids"] = set(STATE["recipes"]["recipe_id"].tolist())
        STATE["known_uids"] = set(STATE["inter"]["user_id"].tolist())
        rec = joblib.load(config.MODELS_DIR / "recommenders.joblib")
        STATE.update(rec)
        try:
            STATE["ua"] = pd.read_csv(config.DATA_PROCESSED_DIR / "user_aspects.csv")
            STATE["ra"] = pd.read_csv(config.DATA_PROCESSED_DIR / "recipe_aspects.csv")
        except FileNotFoundError:
            STATE["ua"] = pd.DataFrame()
            STATE["ra"] = pd.DataFrame()
        try:
            ing = pd.read_csv(config.DATA_PROCESSED_DIR / "ingredient_index.csv")

            def _q(v):
                try:
                    f = float(v)
                    return None if f != f else f
                except (TypeError, ValueError):
                    return None
            STATE["ing_index"] = {str(r): {"name": n, "quantity": _q(q), "unit": u if str(u) != "nan" else "",
                                            "preparation": p if str(p) != "nan" else ""}
                                  for r, n, q, u, p in
                                  zip(ing["raw"], ing["name"], ing["quantity"], ing["unit"], ing["preparation"])}
        except FileNotFoundError:
            STATE["ing_index"] = {}
        try:
            # image-liveness audit: checked-dead photo URLs are suppressed by cards;
            # unchecked ids keep legacy behavior (served, client falls back on error)
            audit = pd.read_csv(config.DATA_PROCESSED_DIR / "image_audit.csv")
            STATE["image_dead"] = {int(r) for r, ok in zip(audit["recipe_id"], audit["image_ok"]) if not ok}
            STATE["image_live"] = {int(r) for r, ok in zip(audit["recipe_id"], audit["image_ok"]) if ok}
        except FileNotFoundError:
            STATE["image_dead"] = set()
            STATE["image_live"] = set()
        try:
            from backend.app.api.cards import set_image_policy
            set_image_policy(STATE.get("image_dead"), STATE.get("image_live"))
        except Exception:
            pass
    except FileNotFoundError:
        pass  # stay up; endpoints return 503 with setup instructions


@app.get("/api/health")
def health():
    ready = "adaptive" in STATE
    info = {"ready": ready}
    if ready:
        try:
            from backend.app import db as appdb
            appdb.fetch_one("SELECT 1")
            info["db"] = "ok"
        except Exception as e:
            info["db"] = f"error: {e}"
        info["recipes"] = len(STATE.get("recipes", []))
        info["interactions"] = len(STATE.get("inter", []))
    else:
        info["detail"] = config.MISSING_DATA_MSG
    return info


@app.get("/api/recipes")
def list_recipes(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                 q: str = ""):
    s = _require_state()
    df = s["recipes"]
    if q:
        df = df[df["name"].str.contains(q, case=False, na=False)]
    return df.iloc[offset:offset + limit][["recipe_id", "name", "minutes"]].to_dict(orient="records")


@app.get("/api/recipes/{recipe_id}")
def recipe_detail(recipe_id: int):
    s = _require_state()
    df = s["recipes"]
    row = df[df["recipe_id"] == recipe_id]
    if row.empty:
        raise HTTPException(404, "Unknown recipe_id")
    r = row.iloc[0]
    from backend.app.api.cards import detail as card_detail
    out = card_detail(r)
    if "ra" in s and len(s["ra"]):
        rr = s["ra"][s["ra"]["recipe_id"] == recipe_id]
        if len(rr):
            out["aspects"] = {c: float(rr.iloc[0][c]) for c in rr.columns if c != "recipe_id" and rr.iloc[0][c] != 0}
    return out


def _enrich(user_id, recs, meta):
    s = STATE
    from backend.app.deps import rmap as _rmap
    rmap = _rmap(s)
    ua = s.get("ua", pd.DataFrame())
    ra = s.get("ra", pd.DataFrame())
    urow = None
    if len(ua) and user_id in set(ua["user_id"]):
        urow = ua[ua["user_id"] == user_id].iloc[0].to_dict()
    out = []
    for r in recs:
        rid = r["recipe_id"]
        name = str(rmap.loc[rid, "name"]) if rid in rmap.index else f"Recipe {rid}"
        rrow = None
        if len(ra) and rid in set(ra["recipe_id"]):
            rrow = ra[ra["recipe_id"] == rid].iloc[0].to_dict()
        parts = {k: r.get(k, 0) for k in ("baseline", "temporal", "aspect")}
        out.append({"recipe_id": rid, "name": name, "score": r["score"], "parts": parts,
                    "explanation": explain(user_id, rid, parts, meta, urow, rrow, s["recipes"])})
    return out


@app.get("/api/recommendations/{user_id}")
def recommend(user_id: int, k: int = Query(10, ge=1, le=50), mode: str = "full"):
    s = _require_state()
    if mode not in ("baseline", "temporal", "aspect", "full"):
        raise HTTPException(422, "mode must be baseline|temporal|aspect|full")
    if user_id not in set(s["inter"]["user_id"]):
        recs = s["baseline"].recommend_new_user(k=k)
        return {"user_id": user_id, "mode": mode, "cold_start": True,
                "recommendations": _enrich(user_id, [{"recipe_id": r["recipe_id"], "score": r["score"],
                                                      "baseline": 0, "temporal": 0, "aspect": 0} for r in recs], {})}
    recs, meta = s["adaptive"].recommend(user_id, k=k, ablation=mode)
    return {"user_id": user_id, "mode": mode, "cold_start": False,
            "shift": meta["shift"], "weights": meta["weights"],
            "recommendations": _enrich(user_id, recs, meta)}


@app.get("/api/preferences/{user_id}")
def preferences(user_id: int):
    from src.recommender import temporal as T
    s = _require_state()
    tp = T.user_temporal_profile(user_id, s["inter"], s["recipes"])
    aspects = {}
    if len(s.get("ua", pd.DataFrame())) and user_id in set(s["ua"]["user_id"]):
        row = s["ua"][s["ua"]["user_id"] == user_id].iloc[0]
        aspects = {c: float(row[c]) for c in s["ua"].columns if c != "user_id" and row[c] != 0}
    return {"user_id": user_id, "shift": tp["shift"], "n_old": tp["n_old"],
            "n_recent": tp["n_recent"], "aspects": aspects}


@app.get("/api/preferences/{user_id}/evolution")
def evolution(user_id: int):
    from src.recommender import temporal as T
    from src.recommender.temporal import split_old_recent
    s = _require_state()
    tp = T.user_temporal_profile(user_id, s["inter"], s["recipes"])
    # representative earlier/recent recipes from REAL history (top-rated, then recent)
    from backend.app.deps import rname as _rname
    rmap = _rname(s)
    g = s["inter"][s["inter"]["user_id"] == user_id].sort_values("date")
    old, recent = split_old_recent(g)
    def names(frame, n=3):
        first = frame.sort_values("date").head(n)  # earliest (old) / latest window start
        return [{"recipe_id": int(r), "name": str(rmap.get(r, f"Recipe {r}")), "rating": int(rt)}
                for r, rt in zip(first["recipe_id"], first["rating"])]
    return {**tp, "earlier_recipes": names(old), "recent_recipes": names(recent)}


@app.get("/api/preferences/{user_id}/aspects")
def aspects(user_id: int):
    s = _require_state()
    if len(s.get("ua", pd.DataFrame())) and user_id in set(s["ua"]["user_id"]):
        row = s["ua"][s["ua"]["user_id"] == user_id].iloc[0]
        return {"user_id": user_id,
                "aspects": {c: float(row[c]) for c in s["ua"].columns if c != "user_id" and row[c] != 0}}
    return {"user_id": user_id, "aspects": {}}


@app.get("/api/recommendations/{user_id}/explanations")
def explanations(user_id: int, k: int = 10):
    r = recommend(user_id, k=k)
    return {"user_id": user_id,
            "explanations": [{**rec, } for rec in r["recommendations"]]}


@app.get("/api/dataset/status")
def dataset_status():
    from src.data import schema
    try:
        rp, ip = schema.resolve_dataset_files()
        return {"present": True, "recipe_file": rp.name, "interaction_file": ip.name}
    except Exception as e:
        return {"present": False, "message": str(e)}


@app.get("/api/demo_users")
def demo_users(min_interactions: int = 15, min_reviews: int = 3, limit: int = 12):
    """Real Food.com users suitable for demonstrating personalization.

    Ranked by review availability then preference shift — all values computed
    from processed data, never fabricated. 269575 (known demo candidate) is
    included first when it qualifies.
    """
    from src.recommender import temporal as T
    s = _require_state()
    inter = s["inter"]
    counts = inter.groupby("user_id").size().sort_values(ascending=False)
    has_review = inter[inter["review"].astype("object").astype(str).str.len() > 0].groupby("user_id").size()
    cands = [int(u) for u in counts[counts >= min_interactions].index[:200]]
    cands = [u for u in cands if has_review.get(u, 0) >= min_reviews]
    if 269575 in set(counts[counts >= min_interactions].index) and 269575 not in cands:
        cands.insert(0, 269575)  # known demo candidate: evaluate first, never cut off
    scored = []
    for u in cands[:60]:
        tp = T.user_temporal_profile(u, inter, s["recipes"])
        aspects = {}
        if len(s.get("ua", pd.DataFrame())) and u in set(s["ua"]["user_id"]):
            row = s["ua"][s["ua"]["user_id"] == u].iloc[0]
            aspects = {c: float(row[c]) for c in s["ua"].columns if c != "user_id" and row[c] != 0}
        scored.append({"user_id": u, "n_interactions": int(counts[u]),
                       "n_reviews": int(has_review.get(u, 0)), "shift": round(tp["shift"], 3),
                       "n_old": tp["n_old"], "n_recent": tp["n_recent"],
                       "n_aspects": len(aspects)})
    scored.sort(key=lambda d: (d["n_aspects"] > 0, d["shift"]), reverse=True)
    if any(d["user_id"] == 269575 for d in scored):
        scored.sort(key=lambda d: d["user_id"] != 269575)
    return {"users": scored[:limit], "default_user_id": 269575 if any(
        d["user_id"] == 269575 for d in scored) else (scored[0]["user_id"] if scored else None)}


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
DIST_DIR = Path(__file__).resolve().parents[2] / "frontend-react" / "dist"
if FRONTEND_DIR.exists():
    # classic static UI kept for reference under /classic
    app.mount("/classic", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="classic")
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    def _spa_root():
        from fastapi.responses import FileResponse
        return FileResponse(str(DIST_DIR / "index.html"))

    @app.get("/{path:path}", include_in_schema=False)
    def _spa_fallback(path: str):
        from fastapi.responses import FileResponse
        if path.startswith(("api/", "docs", "openapi.json", "redoc", "classic", "assets/")):
            from fastapi import HTTPException
            raise HTTPException(404)
        return FileResponse(str(DIST_DIR / "index.html"))
elif FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
