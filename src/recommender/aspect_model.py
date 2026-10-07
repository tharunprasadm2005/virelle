"""Addition #2 — Review-Aspect-Based Preference Learning (local, no paid APIs).

Pipeline: clean -> aspect detection (curated lexicon over unigrams/bigrams,
configurable in ASPECT_VOCAB) -> sentiment per aspect (lexicon + negation
window, optional VADER-style valence) -> aggregate user/recipe profiles ->
cosine compatibility.

Documented limitation: lexicon/rule-based is an interpretable prototype;
see docs/LIMITATIONS.md. Works fully offline.
"""
import re
from collections import defaultdict
import numpy as np
import pandas as pd

ASPECT_VOCAB = {
    "taste": ["taste", "tasty", "flavor", "flavour", "flavorful", "yummy", "delicious", "bland", "tasteless"],
    "sweet": ["sweet", "sugary", "dessert-like"],
    "salty": ["salty", "salt", "saltness", "oversalted"],
    "spicy": ["spicy", "spice", "hot", "peppery", "chili", "chilli", "jalapeno", "cayenne"],
    "healthy": ["healthy", "health", "nutritious", "diet", "low-calorie", "low calorie", "light", "wholesome", "fresh"],
    "oily": ["oily", "greasy", "fatty", "oil"],
    "texture": ["texture", "crunchy", "crisp", "crispy", "chewy", "creamy", "soggy", "tender", "moist", "dry"],
    "easy": ["easy", "simple", "effortless", "straightforward", "beginner"],
    "difficult": ["difficult", "hard", "complicated", "tricky", "challenging"],
    "quick": ["quick", "fast", "minutes", "instant", "5-minute"],
    "slow": ["slow", "long", "hours", "time-consuming", "took forever", "took too long"],
    "cheap": ["cheap", "affordable", "budget", "inexpensive", "economical"],
    "expensive": ["expensive", "costly", "pricey"],
    "filling": ["filling", "hearty", "satisfying", "heavy"],
    "portion": ["portion", "serving", "servings", "yield", "amount"],
    "ingredients": ["ingredient", "ingredients", "substitut"],
    "preparation": ["preparation", "prepare", "prep", "instruction", "direction", "recipe step", "cook time"],
}
POS_WORDS = {"tasty", "delicious", "yummy", "great", "love", "loved", "amazing", "wonderful", "perfect",
             "excellent", "easy", "quick", "healthy", "fresh", "light", "flavorful", "tender", "moist",
             "hearty", "satisfying", "simple", "fast", "affordable", "good", "nice", "best", "enjoyed", "favorite"}
NEG_WORDS = {"bland", "tasteless", "awful", "terrible", "horrible", "hate", "hated", "disgusting", "gross",
             "soggy", "dry", "bad", "worst", "disappointing", "boring", "greasy"}
# NOTE: descriptive aspect words (spicy, sweet, oily, ...) are deliberately NOT in
# NEG_WORDS — negativity comes from evaluative words or an explicit "too/overly"
# construction, so "loved the heat" scores positive while "too spicy" scores negative.
NEGATORS = {"not", "no", "never", "hardly", "barely", "isnt", "wasnt", "dont", "didnt", "without", "lack"}

TOKEN = re.compile(r"[a-z]+(?:-[a-z]+)?")


def _tokens(text):
    return TOKEN.findall(str(text).lower())


def _window_sentiment(tokens, hit_idx, window=2):
    lo = max(0, hit_idx - window)
    hi = min(len(tokens), hit_idx + window + 1)
    win = tokens[lo:hi]
    pos = sum(1 for t in win if t in POS_WORDS)
    neg = sum(1 for t in win if t in NEG_WORDS)
    negated = any(t in NEGATORS for t in win)
    score = pos - neg
    if negated:
        score = -score
    # explicit "too X / overly X" -> negative (only when adjacent to the hit)
    left = tokens[max(0, hit_idx - 2):hit_idx + 1]
    if any(w in {"too", "overly", "over"} for w in left):
        score -= 1
    if score > 0:
        return "positive", min(1.0, 0.5 + 0.25 * score)
    if score < 0:
        return "negative", min(1.0, 0.5 + 0.25 * abs(score))
    return "neutral", 0.0


def extract_review_aspects(review_text):
    """Return {aspect: signed_score in [-1,1]} for one review."""
    toks = _tokens(review_text)
    if len(toks) < 2:
        return {}
    out = {}
    for aspect, keywords in ASPECT_VOCAB.items():
        for kw in keywords:
            parts = kw.split()
            starts = [i for i in range(len(toks) - len(parts) + 1)
                      if toks[i:i + len(parts)] == parts]
            for s in starts:
                sent, conf = _window_sentiment(toks, s)
                val = conf if sent == "positive" else (-conf if sent == "negative" else 0.0)
                if aspect in out:
                    out[aspect] = float(np.clip((out[aspect] + val) / 2, -1, 1))
                else:
                    out[aspect] = float(val)
    return {a: v for a, v in out.items() if v != 0.0}


def build_aspect_tables(inter, max_reviews=None):
    """Aggregate over REAL review texts. Returns (user_profile, recipe_profile) DataFrames."""
    df = inter[inter["review"].astype(str).str.strip().str.len() >= 3].copy()
    if max_reviews and len(df) > max_reviews:
        df = df.sample(n=max_reviews, random_state=42)
    user_acc = defaultdict(lambda: defaultdict(list))
    rec_acc = defaultdict(lambda: defaultdict(list))
    for row in df.itertuples():
        asp = extract_review_aspects(row.review)
        for a, v in asp.items():
            user_acc[int(row.user_id)][a].append(v)
            rec_acc[int(row.recipe_id)][a].append(v)
    aspects = sorted(ASPECT_VOCAB)
    urows = [{**{"user_id": u}, **{a: float(np.mean(v[a])) if a in v else 0.0 for a in aspects}}
             for u, v in user_acc.items()]
    rrows = [{**{"recipe_id": r}, **{a: float(np.mean(v[a])) if a in v else 0.0 for a in aspects}}
             for r, v in rec_acc.items()]
    user_df = pd.DataFrame(urows) if urows else pd.DataFrame(columns=["user_id"] + aspects)
    rec_df = pd.DataFrame(rrows) if rrows else pd.DataFrame(columns=["recipe_id"] + aspects)
    return user_df, rec_df


def aspect_compatibility(user_vec, recipe_vec):
    u = np.asarray(user_vec, dtype=float)
    r = np.asarray(recipe_vec, dtype=float)
    if np.linalg.norm(u) == 0 or np.linalg.norm(r) == 0:
        return 0.0
    # user likes (+) should match recipe expressing (+) and avoid recipe expressing what user dislikes
    return float(u @ r / (np.linalg.norm(u) * np.linalg.norm(r)))
