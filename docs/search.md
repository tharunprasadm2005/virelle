# Search (Phases 6–7)

TF-IDF keyword retrieval is preserved, never replaced.

- `scripts/build_semantic_index.py`: MiniLM (`sentence-transformers/all-MiniLM-L6-v2`,
  384-dim, L2-normalized) over `content_features` → `models/semantic_embeds.npy` +
  `models/semantic_faiss.index` (IndexFlatIP) + `semantic_ids.npy` + meta stamp.
  Resumable via memmap. Full catalog indexed (522,517).
- `src/recommender/semantic_search.py`: lazy loader (800MB+ artifacts never load at
  import/startup) + `search(query, k)` cosine candidates.
- `GET /api/recipes/semantic-search`: raw sidecar output (research/transparency).
- `GET /api/recipes/search?mode=hybrid` (default): min-max-normalized
  `SEARCH_W_KEYWORD`·kw + `SEARCH_W_SEMANTIC`·sem + `SEARCH_W_PREF`·pref
  (cuisine overlap + aspect compatibility), then diet/time/dislike filters.
  Weights in `src/config.py` (0.4/0.3/0.3), echoed in every response.
  `mode=keyword` keeps TF-IDF-first behavior. Research evaluation untouched.

## Limits (honest)
Fusion weights (0.4/0.3/0.3) are v1 defaults, not tuned on relevance judgments;
long natural queries occasionally surface an odd keyword match at rank 1.
Semantic-only candidates score 0 on the keyword part by design (and vice versa).
