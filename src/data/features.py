"""Feature building: TF-IDF content matrix + TruncatedSVD collaborative model.

Baseline parity (see docs/BASELINE_ANALYSIS.md): the original used
scikit-surprise SVD + TF-IDF cosine with hybrid alpha=0.7. Surprise has no
wheels for modern Python on Windows, so CF is implemented with
TruncatedSVD on the user-item matrix — same matrix-factorisation family,
same scoring semantics (predicted rating 1-5 via user/item means + factors).
"""
import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src import config


def build_tfidf(recipes: pd.DataFrame, max_features=20000):
    vec = TfidfVectorizer(max_features=max_features, stop_words="english",
                          ngram_range=(1, 2), min_df=2)
    mat = vec.fit_transform(recipes["content_features"].fillna(""))
    return vec, mat


def build_cf(inter: pd.DataFrame, n_components=50):
    users = np.sort(inter["user_id"].unique())
    items = np.sort(inter["recipe_id"].unique())
    uix = {u: i for i, u in enumerate(users)}
    iix = {r: i for i, r in enumerate(items)}
    rows = inter["user_id"].map(uix).to_numpy()
    cols = inter["recipe_id"].map(iix).to_numpy()
    global_mean = float(inter["rating"].mean())
    # mean-centered matrix for SVD
    data = (inter["rating"].to_numpy(dtype=float) - global_mean)
    mat = csr_matrix((data, (rows, cols)), shape=(len(users), len(items)))
    k = max(2, min(n_components, min(mat.shape) - 1))
    svd = TruncatedSVD(n_components=k, random_state=config.RANDOM_STATE)
    user_factors = svd.fit_transform(mat)
    item_factors = svd.components_.T  # n_items x k
    user_means = np.zeros(len(users))  # already centered globally; keep per-user bias
    ub = inter.groupby("user_id")["rating"].mean()
    for u, m in ub.items():
        user_means[uix[u]] = float(m) - global_mean
    ib = inter.groupby("recipe_id")["rating"].mean()
    item_means = np.zeros(len(items))
    for r, m in ib.items():
        item_means[iix[r]] = float(m) - global_mean
    model = {"svd": svd, "user_factors": user_factors, "item_factors": item_factors,
             "users": users, "items": items, "uix": uix, "iix": iix,
             "global_mean": global_mean, "user_means": user_means, "item_means": item_means}
    return model


def cf_predict(model, user_id, recipe_id):
    gm = model["global_mean"]
    uix, iix = model["uix"], model["iix"]
    pred = gm
    if user_id in uix:
        pred += model["user_means"][uix[user_id]]
    if recipe_id in iix:
        pred += model["item_means"][iix[recipe_id]]
    if user_id in uix and recipe_id in iix:
        pred += float(model["user_factors"][uix[user_id]] @ model["item_factors"][iix[recipe_id]])
    return float(np.clip(pred, 1.0, 5.0))


def content_scores(seed_ids, recipes, tfidf_matrix, topn=200):
    idx = recipes.index[recipes["recipe_id"].isin(set(seed_ids))].tolist()
    if not idx:
        return {}
    sims = cosine_similarity(tfidf_matrix[idx], tfidf_matrix).max(axis=0)
    order = np.argsort(sims)[::-1]
    out = {}
    for j in order:
        rid = int(recipes.iloc[j]["recipe_id"])
        if rid not in seed_ids:
            out[rid] = float(sims[j])
            if len(out) >= topn:
                break
    return out


def save_artifacts(path, obj):
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(obj, path)


def load_artifacts(path):
    return joblib.load(path)
