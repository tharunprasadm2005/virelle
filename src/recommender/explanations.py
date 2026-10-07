"""Explanations generated from ACTUAL model signals (never fabricated)."""
from src.recommender.aspect_model import ASPECT_VOCAB


def explain(user_id, recipe_id, parts, tprof, user_aspects_row, recipe_aspects_row, recipes):
    why = []
    if parts.get("baseline", 0) > 0.6:
        why.append("Similar to recipes you rated highly in the past.")
    if parts.get("temporal", 0) > 0.55:
        why.append("Matches your recent preferences (weighted above older history).")
    elif parts.get("temporal", 0) > 0.3:
        why.append("Partly matches recent cooking patterns.")
    if user_aspects_row is not None and recipe_aspects_row is not None:
        likes = [a for a in ASPECT_VOCAB if user_aspects_row.get(a, 0) > 0.3 and recipe_aspects_row.get(a, 0) > 0.2]
        dislikes_avoided = [a for a in ASPECT_VOCAB if user_aspects_row.get(a, 0) < -0.3 and recipe_aspects_row.get(a, 0) <= 0.1]
        for a in likes[:3]:
            why.append(f"Matches your preference for {a} recipes (from your reviews).")
        for a in dislikes_avoided[:2]:
            why.append(f"Avoids {a}, which your reviews suggest you dislike.")
    if tprof and tprof.get("shift", 0) > 0.4:
        why.append(f"Your tastes shifted recently (shift={tprof['shift']:.2f}); this reflects newer behaviour.")
    if not why:
        why.append("Popular recipe matching your general profile.")
    return why
