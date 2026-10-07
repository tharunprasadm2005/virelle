"""Offline semantic embeddings: MiniLM over content_features -> FAISS IndexFlatIP.

Resumable (memmap + meta count), chunked checkpoints. Full catalog:
522K x 384 float32 ~= 800MB. Run once; search loads lazily (see api/search.py).
Meta stamps model name/version for reproducibility (Phase 29 versioning).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src import config

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIM = 384


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    rec = pd.read_csv(config.DATA_PROCESSED_DIR / "recipes_processed.csv",
                      usecols=["recipe_id", "content_features"])
    if args.limit:
        rec = rec.head(args.limit)
    n = len(rec)
    emb_path = config.MODELS_DIR / "semantic_embeds.npy"
    meta_path = config.MODELS_DIR / "semantic_index_meta.json"
    done = 0
    if emb_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("model") == MODEL_NAME and meta.get("n_total") == n:
            done = meta.get("n_done", 0)
    print(f"Embedding {n} recipes from {done} (model {MODEL_NAME}).")
    emb = np.memmap(str(emb_path), dtype="float32", mode="w+" if done == 0 else "r+", shape=(n, DIM))
    ids = rec["recipe_id"].to_numpy()
    np.save(str(config.MODELS_DIR / "semantic_ids.npy"), ids)
    from sentence_transformers import SentenceTransformer
    import torch
    model = SentenceTransformer(MODEL_NAME)
    model.max_seq_length = 128
    texts = rec["content_features"].fillna("").tolist()
    bs = args.batch
    with torch.no_grad():
        for s in range(done, n, bs):
            chunk = model.encode(texts[s:s + bs], batch_size=bs, show_progress_bar=False,
                                 convert_to_numpy=True, normalize_embeddings=True)
            emb[s:s + len(chunk)] = chunk.astype("float32")
            emb.flush()
            if (s // bs) % 20 == 0:
                meta_path.write_text(json.dumps({"model": MODEL_NAME, "dim": DIM,
                                                 "n_total": n, "n_done": s + len(chunk),
                                                 "updated": datetime.now(timezone.utc).isoformat()}))
                print(f"  {s + len(chunk)}/{n}")
    meta_path.write_text(json.dumps({"model": MODEL_NAME, "dim": DIM, "n_total": n,
                                     "n_done": n, "built_at": datetime.now(timezone.utc).isoformat()}))
    import faiss
    index = faiss.IndexFlatIP(DIM)
    step = 50000
    for s in range(0, n, step):
        index.add(np.asarray(emb[s:s + step]))
    faiss.write_index(index, str(config.MODELS_DIR / "semantic_faiss.index"))
    print("Wrote embeddings + FAISS index.")


if __name__ == "__main__":
    main()
