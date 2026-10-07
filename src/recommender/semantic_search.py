"""Semantic retrieval sidecar: MiniLM + FAISS over recipe content_features.

TF-IDF is NOT replaced (keyword path stays). This module loads the offline
artifacts lazily (800MB+ — never at import/startup) and returns candidate ids
with cosine scores. Personalization fusion happens in the product ranking layer.
"""
import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_index = None
_ids = None


def _load():
    global _model, _index, _ids
    from src import config
    if _index is not None:
        return
    import faiss
    from sentence_transformers import SentenceTransformer
    idx_path = config.MODELS_DIR / "semantic_faiss.index"
    ids_path = config.MODELS_DIR / "semantic_ids.npy"
    if not idx_path.exists():
        raise FileNotFoundError("Semantic index missing — run scripts/build_semantic_index.py")
    _model = SentenceTransformer(MODEL_NAME)
    _model.max_seq_length = 128
    _index = faiss.read_index(str(idx_path))
    _ids = np.load(str(ids_path))


def available() -> bool:
    from src import config
    return (config.MODELS_DIR / "semantic_faiss.index").exists()


def search(query: str, k: int = 100):
    """(recipe_ids, cosine_scores) for a natural-language query."""
    _load()
    q = _model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
    scores, pos = _index.search(q, k)
    return [int(_ids[p]) for p in pos[0] if p >= 0], [float(s) for s in scores[0][:len(pos[0])]]
