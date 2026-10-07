"""Central configuration. All paths relative to project root (portable)."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATA_EXTERNAL_DIR = PROJECT_ROOT / "data" / "external"
MODELS_DIR = PROJECT_ROOT / "models"
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"
REPORTS_FIG_DIR = PROJECT_ROOT / "reports" / "figures"

EXPECTED_RECIPE_FILES = ["RAW_recipes.csv", "recipes.csv", "Recipes.csv"]
EXPECTED_INTERACTION_FILES = ["RAW_interactions.csv", "RAW_reviews.csv", "interactions.csv", "reviews.csv", "Reviews.csv"]

DATASET_URL = "https://www.kaggle.com/datasets/irkaal/foodcom-recipes-and-reviews"
MISSING_DATA_MSG = (
    "Food.com dataset not found. Download the dataset from Kaggle "
    f"({DATASET_URL}) and place RAW_recipes.csv and RAW_interactions.csv in data/raw/. "
    "See data/README.md and docs/DATASET.md for details."
)

DATA_MODE = os.getenv("DATA_MODE", "sample").lower()  # full | sample (sample = real subset, never synthetic)
SAMPLE_N_RECIPES = int(os.getenv("SAMPLE_N_RECIPES", "10000"))
SAMPLE_N_INTERACTIONS = int(os.getenv("SAMPLE_N_INTERACTIONS", "100000"))
RANDOM_STATE = int(os.getenv("RANDOM_STATE", "42"))

W_BASELINE = float(os.getenv("W_BASELINE", "0.5"))
W_TEMPORAL = float(os.getenv("W_TEMPORAL", "0.25"))
W_ASPECT = float(os.getenv("W_ASPECT", "0.25"))

TEMPORAL_MODE = os.getenv("TEMPORAL_MODE", "exp_decay")  # exp_decay | window
TEMPORAL_LAMBDA = float(os.getenv("TEMPORAL_LAMBDA", "0.02"))
HIST_WEIGHT = float(os.getenv("HIST_WEIGHT", "0.3"))
RECENT_WEIGHT = float(os.getenv("RECENT_WEIGHT", "0.7"))

HYBRID_ALPHA = 0.7  # baseline-internal: CF vs content split (preserved from baseline_original)

MIN_RATINGS_USER = 5
MIN_RATINGS_RECIPE = 3

# Cook (what-can-i-cook) ranking weights: coverage + personalization + quality.
# Documented and tunable via env; final score is a weighted blend, not pure overlap.
COOK_W_COVERAGE = float(os.getenv("COOK_W_COVERAGE", "0.5"))
COOK_W_PREF = float(os.getenv("COOK_W_PREF", "0.3"))
COOK_W_QUALITY = float(os.getenv("COOK_W_QUALITY", "0.2"))

# Product search fusion weights (keyword + semantic + preference). Tunable via env.
# Research TF-IDF/CF pipeline is separate and untouched by these.
SEARCH_W_KEYWORD = float(os.getenv("SEARCH_W_KEYWORD", "0.4"))
SEARCH_W_SEMANTIC = float(os.getenv("SEARCH_W_SEMANTIC", "0.3"))
SEARCH_W_PREF = float(os.getenv("SEARCH_W_PREF", "0.3"))

# Freshness/fatigue penalties (product layer only; research model untouched).
FATIGUE_SHOWN_PENALTY = float(os.getenv("FATIGUE_SHOWN_PENALTY", "0.08"))
FATIGUE_COOKED_PENALTY = float(os.getenv("FATIGUE_COOKED_PENALTY", "0.25"))
FATIGUE_MAX_SAME_TAG = int(os.getenv("FATIGUE_MAX_SAME_TAG", "4"))


def validate_weights():
    total = W_BASELINE + W_TEMPORAL + W_ASPECT
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Hybrid weights must sum to 1.0, got {total}")
