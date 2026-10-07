"""Loading of the REAL Food.com CSVs (no synthetic data anywhere in this path)."""
import pandas as pd
from src.data import schema


def _plain_strings(df):
    """pandas>=3 uses 'str' dtype for text; convert to plain object dtype
    to avoid giant numpy conversions on fillna/astype downstream."""
    import pandas.api.types as pat
    for c in df.columns:
        try:
            if pat.is_string_dtype(df[c]) and str(df[c].dtype) != "object":
                df[c] = df[c].astype("object")
        except Exception:
            pass
    return df


def load_raw(raw_dir=None, nrows=None):
    recipe_path, inter_path = schema.resolve_dataset_files(raw_dir)
    recipes = _plain_strings(pd.read_csv(recipe_path, nrows=nrows))
    inter = _plain_strings(pd.read_csv(inter_path, nrows=nrows))
    recipes, rmap = schema.validate_and_canonicalise(recipes, schema.RECIPE_COLUMNS, schema.REQUIRED_RECIPE, "recipes")
    inter, imap = schema.validate_and_canonicalise(inter, schema.INTERACTION_COLUMNS, schema.REQUIRED_INTERACTION, "interactions")
    return recipes, inter, {"recipe_file": str(recipe_path), "interaction_file": str(inter_path),
                            "recipe_map": rmap, "interaction_map": imap}
