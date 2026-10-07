"""CRF ingredient parsing via ingredient-parser (strangetom, MIT, v2.8.0).

Library is used AS A LIBRARY for structured qty/unit/name/preparation.
Never raises on bad input (returns ok=False with the original preserved).
Rule-based normalize.py remains the total-coverage fallback for names.

Requires NLTK data: averaged_perceptron_tagger_eng (one-time setup, see README).
"""
import logging

log = logging.getLogger(__name__)

PARSER_NAME = "ingredient-parser"
PARSER_VERSION = "2.8.0"


def _frac_to_float(fr) -> float | None:
    try:
        return float(fr)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def parse_one(text: str) -> dict:
    """Parse one ingredient string. Always returns a dict; ok=False on failure."""
    original = "" if text is None else str(text)
    if not original.strip():
        return {"original": original, "ok": False, "reason": "empty"}
    try:
        from ingredient_parser import parse_ingredient
        r = parse_ingredient(original)
    except Exception as e:  # malformed input, missing model data, etc.
        log.debug("parse failed for %r: %s", original[:60], e)
        return {"original": original, "ok": False, "reason": type(e).__name__}
    try:
        names = [t.text for t in (r.name or [])]
        name = " ".join(names).strip()
        prep = r.preparation.text if r.preparation is not None else ""
        size = r.size.text if getattr(r, "size", None) is not None else ""
        comment = r.comment.text if getattr(r, "comment", None) is not None else ""
        amounts = []
        for a in (r.amount or []):
            amounts.append({"quantity": _frac_to_float(a.quantity),
                            "quantity_max": _frac_to_float(a.quantity_max),
                            "unit": str(a.unit).lower(),
                            "confidence": float(getattr(a, "confidence", 0.0) or 0.0)})
        confs = [t.confidence for t in (r.name or []) if getattr(t, "confidence", None)]
        return {"original": original, "ok": bool(name), "name": name,
                "quantity": amounts[0]["quantity"] if amounts else None,
                "quantity_max": amounts[0]["quantity_max"] if amounts else None,
                "unit": amounts[0]["unit"] if amounts else "",
                "amounts": amounts, "preparation": prep or "", "size": size or "",
                "comment": comment or "",
                "confidence": float(sum(confs) / len(confs)) if confs else 0.0}
    except Exception as e:
        return {"original": original, "ok": False, "reason": type(e).__name__}
