"""Phase 6 tests: semantic sidecar contract on a tiny in-memory FAISS index."""
import numpy as np


def _tiny_index(monkeypatch=None):
    import faiss
    from src.recommender import semantic_search as sem
    vecs = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.7, 0.7, 0.0]], dtype="float32")
    vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    idx = faiss.IndexFlatIP(3)
    idx.add(vecs)
    sem._index = idx
    sem._ids = np.array([11, 22, 33])
    sem._model = type("M", (), {"encode": lambda self, t, **k: np.array([[1.0, 0.0, 0.0]], dtype="float32")})()
    return sem


def test_semantic_contract():
    sem = _tiny_index()
    ids, scores = sem.search("anything", k=2)
    assert ids[0] == 11 and scores[0] > 0.99
    assert len(ids) == 2
    from src.recommender import semantic_search as sem2
    sem2._index = None
    sem2._ids = None
    sem2._model = None
