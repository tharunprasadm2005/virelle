# Limitations & future work

- Aspect NLP is lexicon/rule-based (interpretable, offline, no paid APIs) — sarcasm, implicit
  aspects, and multi-aspect compositionality are limited; embedding/ABSA upgrade is future work (optional LLM stays opt-in).
- Surprise SVD replaced by TruncatedSVD for portability — same family, but exact baseline numbers
  are not bit-identical to the original environment.
- Temporal split evaluation needs users with ≥5 interactions; sparse users fall back to popularity.
- Full Food.com scale needs ~8 GB RAM and 15–30 min preprocessing; use `DATA_MODE=sample` (real subset) for iteration.
- Frontend is a dependency-free static app (no React build) — chosen for runnable-locally reliability.
- No invented metrics: `docs/EXPERIMENTS.md` stays blank until `scripts/evaluate.py` runs on real data.
