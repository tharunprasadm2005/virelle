"""Preprocessing for REAL Food.com data.

Decisions (documented, see docs/METHODOLOGY.md):
- duplicate (user_id, recipe_id): keep most recent by date (else max rating)
- rating==0 dropped (means 'review only', not a valid 1-5 rating) — matches baseline
- missing review text -> "" (aspect pipeline skips empties); missing rating row dropped for CF but kept count
- missing timestamps -> median date of that user else global median; flagged in report
- invalid recipe_ids (in interactions but not recipes) dropped
- malformed nutrition values coerced to NaN; empty ingredients -> []
- extremely short reviews (<3 chars) treated as missing text, rating kept
- activity filtering: users>=MIN_RATINGS_USER, recipes>=MIN_RATINGS_RECIPE (configurable; skipped in sample-debug only if it would empty the frame)
"""
import ast
import logging
import re
import numpy as np
import pandas as pd
from src import config

log = logging.getLogger(__name__)


def _parse_r_vector(s):
    """Parse R-style c("a", "b", NA) vectors from the Food.com CSVs.

    Tokenizer-based (quoted strings or bare NA), so commas INSIDE quoted
    values (e.g. image URLs like .../w_555,h_416,...) never split items.
    """
    body = s.strip()
    if body[:2] == "c(" and body.endswith(")"):
        body = body[2:-1]
    out = []
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|NA(?=\s*,|\s*$)', body):
        tok = m.group(1)
        if tok is None:
            continue  # bare NA
        t = tok.strip()
        if t:
            out.append(t)
    return out


def _as_list(x):
    if isinstance(x, list):
        return [str(i) for i in x]
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return []
    s = str(x).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            v = ast.literal_eval(s)
            if isinstance(v, list):
                return [str(i) for i in v]
        except (ValueError, SyntaxError):
            pass
    if s.startswith("c(") or s.startswith("c ("):
        try:
            return _parse_r_vector(s)
        except Exception:
            pass
    # comma/semicolon separated fallback
    return [t.strip(" '\"") for t in s.replace(";", ",").split(",") if t.strip(" '\"")]


def parse_minutes_value(x):
    """Numeric minutes or ISO-8601 duration (PT24H45M) as in TotalTime/CookTime."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip()
    if not s:
        return np.nan
    m = re.match(r"^PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?$", s)
    if m:
        h, mn, sec = (float(g) if g else 0.0 for g in m.groups())
        return h * 60 + mn + sec / 60
    try:
        return float(s)
    except ValueError:
        return np.nan


def preprocess_recipes(recipes: pd.DataFrame):
    df = recipes.copy()
    rid = "recipe_id" if "recipe_id" in df.columns else "id"
    if rid != "recipe_id":
        df = df.rename(columns={rid: "recipe_id"})
    df["recipe_id"] = pd.to_numeric(df["recipe_id"], errors="coerce")
    df = df.dropna(subset=["recipe_id"])
    df["recipe_id"] = df["recipe_id"].astype(np.int64)
    df = df.drop_duplicates(subset=["recipe_id"], keep="first")
    df["name"] = df["name"].fillna("Unnamed Recipe").astype("object") if "name" in df.columns else "Recipe " + df["recipe_id"].astype(str)
    if "name" not in df.columns:
        df["name"] = "Recipe " + df["recipe_id"].astype(str)
    df["description"] = df["description"].fillna("").astype("object") if "description" in df.columns else ""
    for col in ["ingredients", "tags"]:
        df[col] = df[col].apply(_as_list) if col in df.columns else [[] for _ in range(len(df))]
    # strip R-vector quote artefacts (e.g. '"low' -> 'low'); drop bare punctuation tokens
    def _clean(tok):
        t = str(tok).replace('"', "").replace("'", "").strip()
        return t if len(t) >= 2 and t not in {"<>", "--"} else ""
    for col in ["ingredients", "tags"]:
        df[col] = df[col].apply(lambda l: sorted({c for c in (_clean(t) for t in l) if c}) or [])
    # keep RecipeCategory alongside Keywords when both exist
    if "recipecategory" in df.columns:
        cats = df["recipecategory"].fillna("").astype(str)
        df["tags"] = [sorted(set(t) | ({c.strip()} if c.strip() else set()))
                       for t, c in zip(df["tags"], cats)]
    if "minutes" in df.columns:
        df["minutes"] = df["minutes"].apply(parse_minutes_value)
        df["minutes"] = df["minutes"].replace([np.inf, -np.inf], np.nan).clip(upper=1440)
        med = df["minutes"].median()
        df["minutes"] = df["minutes"].fillna(med if pd.notna(med) else 30).round().astype("int32")
    else:
        df["minutes"] = np.int32(30)
    img_col = next((c for c in df.columns if str(c).strip().lower() == "images"), None)
    if img_col is not None:
        def _first_url(x):
            # first COMPLETE http(s) URL; truncated/partial fragments are rejected
            for u in _as_list(x):
                s = str(u).strip()
                if re.match(r"^https?://\S+$", s) and '"' not in s and " " not in s:
                    return s
            return ""
        df["image_url"] = df[img_col].apply(_first_url)
    else:
        df["image_url"] = ""
    df["ingredients_text"] = df["ingredients"].apply(lambda l: " ".join(s.lower() for s in l))
    df["tags_text"] = df["tags"].apply(lambda l: " ".join(s.lower() for s in l))
    df["content_features"] = (df["name"].astype("object").fillna("") + " " + df["description"].astype("object").fillna("")
                              + " " + df["ingredients_text"] + " " + df["tags_text"])
    return df


def preprocess_interactions(inter, valid_recipe_ids=None):
    df = inter.copy()
    df["user_id"] = pd.to_numeric(df["user_id"], errors="coerce")
    df["recipe_id"] = pd.to_numeric(df["recipe_id"], errors="coerce")
    df = df.dropna(subset=["user_id", "recipe_id"])
    df["user_id"] = df["user_id"].astype(np.int64)
    df["recipe_id"] = df["recipe_id"].astype(np.int64)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating"])
    df = df[df["rating"] > 0]  # 0 = review-only, not a valid 1-5 rating (matches baseline)
    df["rating"] = df["rating"].round().astype(int).clip(1, 5)
    if "review" in df.columns:
        # NOTE (pandas>=3): assigning strings re-infers Arrow-backed `str` dtype,
        # and .loc-setitem into such columns explodes memory. Build once, never setitem after.
        raw = df["review"].tolist()
        cleaned = np.array(
            [v if (isinstance(v, str) and len(v.strip()) >= 3) else "" for v in raw],
            dtype=object,
        )
        df = df.drop(columns=["review"])
        df["review"] = pd.Series(cleaned, index=df.index)
    else:
        df["review"] = ""
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if df["date"].isna().any():
            med = df["date"].median()
            df["date"] = df["date"].fillna(med if pd.notna(med) else pd.Timestamp("2015-01-01"))
        df = df.sort_values("date").drop_duplicates(subset=["user_id", "recipe_id"], keep="last")
    else:
        df["date"] = pd.Timestamp("2015-01-01")
        df = df.sort_values("rating").drop_duplicates(subset=["user_id", "recipe_id"], keep="last")
    if valid_recipe_ids is not None:
        df = df[df["recipe_id"].isin(set(valid_recipe_ids))]
    # activity filtering (skip if it would wipe the frame, e.g. tiny debug subsets)
    for col, thresh in (("user_id", config.MIN_RATINGS_USER), ("recipe_id", config.MIN_RATINGS_RECIPE)):
        counts = df[col].value_counts()
        keep = set(counts[counts >= thresh].index)
        if len(keep) >= 2:
            df = df[df[col].isin(keep)]
    df = df.reset_index(drop=True)
    return df


def sample_real_subset(recipes, inter, n_recipes=None, n_inter=None, seed=42):
    """Deterministic REAL subset for dev/debug (DATA_MODE=sample). Not synthetic."""
    import numpy as np
    rng = np.random.RandomState(seed)
    n_recipes = n_recipes or config.SAMPLE_N_RECIPES
    n_inter = n_inter or config.SAMPLE_N_INTERACTIONS
    r = recipes if len(recipes) <= n_recipes else recipes.sample(n=n_recipes, random_state=seed).sort_values("recipe_id")
    keep_ids = set(r["recipe_id"])
    i = inter[inter["recipe_id"].isin(keep_ids)]
    if len(i) > n_inter:
        i = i.sample(n=n_inter, random_state=seed).sort_values(["user_id", "date"])
    # re-trim recipes to those actually referenced (still real rows only)
    used = set(i["recipe_id"]) | set(r["recipe_id"].head(min(len(r), n_recipes)).tolist())
    r = recipes[recipes["recipe_id"].isin(used)].copy() if len(i) else r
    return r.reset_index(drop=True), i.reset_index(drop=True)
