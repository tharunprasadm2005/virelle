"""Addition #1 — Preference Evolution Over Time.

- Interactions sorted chronologically per user.
- Weighting: exp_decay w=exp(-lambda*age_days) [default] or window
  (recent 1.0 / medium 0.6 / old 0.3 by recency tercile).
- Old vs recent profiles: recipe-tag/ingredient preference vectors +
  nutrition/time means; shift = cosine distance (interpretable).
- Adaptive profile = HIST_WEIGHT*historical + RECENT_WEIGHT*recent.
All params configurable via src/config.py / env.
"""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src import config


def interaction_weights(dates, mode=None, lam=None, ref_date=None):
    mode = mode or config.TEMPORAL_MODE
    lam = config.TEMPORAL_LAMBDA if lam is None else lam
    dates = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    ref = pd.to_datetime(ref_date) if ref_date is not None else dates.max()
    age = (ref - dates).dt.total_seconds() / 86400.0
    if mode == "window":
        q1, q2 = age.quantile(1 / 3), age.quantile(2 / 3)
        return age.apply(lambda a: 1.0 if a <= q1 else (0.6 if a <= q2 else 0.3)).to_numpy(float)
    return np.exp(-lam * age.to_numpy(float))  # exp_decay


def split_old_recent(user_inter, frac_recent=0.4):
    u = user_inter.sort_values("date").reset_index(drop=True)
    n = len(u)
    if n < 4:
        return u.iloc[0:0], u  # too little history: everything is 'recent'
    cut = max(1, int(n * (1 - frac_recent)))
    return u.iloc[:cut], u.iloc[cut:]


def _profile_vector(frames_tags_texts):
    if not frames_tags_texts:
        return None, None
    vec = TfidfVectorizer(stop_words="english", max_features=2000)
    try:
        mat = vec.fit_transform(frames_tags_texts)
    except ValueError:
        return None, None
    return vec, np.asarray(mat.mean(axis=0)).ravel()


def preference_shift(old_texts, recent_texts):
    """Cosine distance between old and recent TF-IDF mean vectors in [0,1]."""
    if not old_texts or not recent_texts:
        return 0.0
    vocab = sorted(set(" ".join(old_texts + recent_texts).split()))
    if not vocab:
        return 0.0
    vec = TfidfVectorizer(vocabulary=vocab)
    try:
        m = vec.fit_transform(old_texts + recent_texts)
    except ValueError:
        return 0.0
    o = np.asarray(m[:len(old_texts)].mean(axis=0)).ravel()
    r = np.asarray(m[len(old_texts):].mean(axis=0)).ravel()
    if np.linalg.norm(o) == 0 or np.linalg.norm(r) == 0:
        return 0.0
    sim = float(cosine_similarity([o], [r])[0, 0])
    return float(np.clip(1.0 - sim, 0.0, 1.0))


def user_temporal_profile(user_id, inter, recipes, mode=None, lam=None):
    u = inter[inter["user_id"] == user_id].copy()
    if u.empty:
        return {"user_id": user_id, "shift": 0.0, "n_old": 0, "n_recent": 0,
                "adaptive_pref_text": "", "recent_pref_text": "", "old_pref_text": ""}
    u = u.sort_values("date")
    w = interaction_weights(u["date"], mode=mode, lam=lam)
    u = u.assign(weight=w)
    old, recent = split_old_recent(u)
    rmap = recipes.set_index("recipe_id")
    def texts(frame):
        t = []
        for rid in frame["recipe_id"]:
            if rid in rmap.index:
                t.append(str(rmap.loc[rid, "tags_text"]) + " " + str(rmap.loc[rid, "ingredients_text"]))
        return t
    old_t, rec_t = texts(old), texts(recent)
    shift = preference_shift(old_t, rec_t)
    # adaptive preference text: weight recent more
    hw, rw = config.HIST_WEIGHT, config.RECENT_WEIGHT
    adaptive = " ".join(old_t * (1 if hw >= rw else 0) + rec_t * (2 if rw > hw else 1))
    return {"user_id": user_id, "shift": shift, "n_old": len(old), "n_recent": len(recent),
            "adaptive_pref_text": adaptive or " ".join(rec_t),
            "recent_pref_text": " ".join(rec_t), "old_pref_text": " ".join(old_t),
            "mean_weight_recent": float(recent["weight"].mean()) if len(recent) else 0.0,
            "mean_weight_old": float(old["weight"].mean()) if len(old) else 0.0}


def temporal_boost(candidate_ids, content_by_id, recent_pref_text, topn_weight=1.0):
    """Score candidates by TF-IDF cosine to the user's recent preference text.

    content_by_id: dict recipe_id -> text (prebuilt once; avoids re-indexing
    a 500K-row frame per user).
    """
    if not recent_pref_text.strip():
        return {int(r): 0.0 for r in candidate_ids}
    docs = [str(content_by_id.get(r, "")) for r in candidate_ids]
    vec = TfidfVectorizer(stop_words="english", max_features=5000)
    try:
        mat = vec.fit_transform([recent_pref_text] + docs)
    except ValueError:
        return {int(r): 0.0 for r in candidate_ids}
    sims = cosine_similarity(mat[0:1], mat[1:]).ravel()
    return {int(r): float(s) * topn_weight for r, s in zip(candidate_ids, sims)}
