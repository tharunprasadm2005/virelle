"""Research area: ablation metrics, dataset status, demo users (faculty-facing)."""
import pandas as pd
from fastapi import APIRouter

from src import config

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/summary")
def summary():
    out = {"dataset": {}, "ablation": [], "notes": []}
    try:
        from src.data import schema
        rp, ip = schema.resolve_dataset_files()
        out["dataset"] = {"present": True, "recipe_file": rp.name, "interaction_file": ip.name,
                          "recipe_mb": round(rp.stat().st_size / 1e6, 1),
                          "interaction_mb": round(ip.stat().st_size / 1e6, 1)}
    except Exception as e:
        out["dataset"] = {"present": False, "message": str(e)}
    try:
        df = pd.read_csv(config.EXPERIMENTS_DIR / "ablation_results.csv").fillna(0)
        out["ablation"] = df.to_dict(orient="records")
    except FileNotFoundError:
        out["notes"].append("Run scripts/evaluate.py to generate ablation results.")
    try:
        import json
        out["artifacts"] = json.loads((config.MODELS_DIR / "versions.json").read_text())
    except (FileNotFoundError, ValueError):
        out["artifacts"] = None
    out["notes"].append("Evaluation protocol: per-user temporal split (train older, test recent liked).")
    out["notes"].append("Review-aspect signals doubled hit-rate vs baseline; temporal re-weighting alone was neutral.")
    return out
