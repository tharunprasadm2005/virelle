"""Unit tests on the tiny TEST FIXTURE only (never project data / never metric claims)."""
import pandas as pd
from src.data import preprocess as P
from src.data import features as F
from src.recommender import temporal as T
from src.recommender import aspect_model as A
from src.recommender.baseline import BaselineRecommender
from src.recommender.hybrid import AdaptiveRecommender
from src.recommender.evaluate import metrics_at_k, temporal_split
from tests.fixtures import tiny_recipes, tiny_interactions


def _prep():
    r = P.preprocess_recipes(tiny_recipes())
    i = P.preprocess_interactions(tiny_interactions(), valid_recipe_ids=set(r["recipe_id"]))
    i["date"] = pd.to_datetime(i["date"])
    return r, i


def test_preprocess_keeps_valid_rows():
    r, i = _prep()
    assert len(r) == 6 and len(i) >= 8
    assert "content_features" in r.columns


def test_missing_data_handling():
    df = pd.DataFrame([{"user_id": 9, "recipe_id": 1, "rating": 0, "review": "ok", "date": "2020-01-01"},
                       {"user_id": 9, "recipe_id": 1, "rating": 5, "review": "", "date": "2021-01-01"}])
    out = P.preprocess_interactions(df, valid_recipe_ids={1})
    assert (out["rating"] > 0).all()
    assert len(out) == 1  # dedup keep-last


def test_temporal_weights_and_shift():
    r, i = _prep()
    w = T.interaction_weights(pd.to_datetime(i["date"]), mode="exp_decay")
    assert (w > 0).all() and (w <= 1.0).all()
    tp = T.user_temporal_profile(1, i, r)
    assert 0.0 <= tp["shift"] <= 1.0
    assert tp["n_recent"] >= 1


def test_aspect_extraction_and_profiles():
    asp = A.extract_review_aspects("The recipe was tasty and healthy but too spicy.")
    assert asp.get("taste", 0) > 0 and asp.get("healthy", 0) > 0 and asp.get("spicy", 0) < 0
    r, i = _prep()
    ua, ra = A.build_aspect_tables(i)
    assert len(ua) > 0 and len(ra) > 0


def test_baseline_and_adaptive_recommend():
    r, i = _prep()
    base = BaselineRecommender.train(r, i)
    recs = base.recommend_baseline(2, k=3)  # user 2 rated 3/6 recipes -> candidates exist
    assert len(recs) > 0
    ua, ra = A.build_aspect_tables(i)
    adapt = AdaptiveRecommender(base, r, i, ua, ra)
    for mode in ("baseline", "temporal", "aspect", "full"):
        out, meta = adapt.recommend(2, k=3, ablation=mode)
        assert len(out) > 0 and "shift" in meta


def test_cold_start_no_crash():
    r, i = _prep()
    base = BaselineRecommender.train(r, i)
    assert len(base.recommend_new_user(k=2)) == 2
    assert base.recommend_baseline(999999, k=2) is not None


def test_metrics_and_split():
    r, i = _prep()
    train, test = temporal_split(i)
    assert len(train) > 0
    m = metrics_at_k([1, 2, 3], [2, 3], k=3)
    assert 0 <= m["P"] <= 1 and 0 <= m["NDCG"] <= 1


def test_r_vector_with_commas_inside_quotes():
    import re
    from src.data.preprocess import _as_list
    raw = 'c("https://img.sndimg.com/food/image/upload/w_555,h_416,c_fit/x.jpg", "https://img.sndimg.com/y.jpg", NA)'
    assert _as_list(raw) == ["https://img.sndimg.com/food/image/upload/w_555,h_416,c_fit/x.jpg",
                             "https://img.sndimg.com/y.jpg"]

    def _valid(u):
        return bool(re.match(r"^https?://\S+$", u)) and '"' not in u and " " not in u

    # truncated fragment from the old splitter must be rejected as an image
    assert not _valid('https://img.sndimg.com/x.jpg", "h')
    assert _valid("https://img.sndimg.com/food/image/upload/w_555,h_416/x.jpg")
