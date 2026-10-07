# Experiments — REAL Food.com results

Protocol (`scripts/evaluate.py`, real data only):
per-user temporal split (train on OLDER interactions, test on recent liked with
rating ≥ 4 — this directly rewards temporal adaptation). Full data:
train = 684,000 / test = 170,929 recent liked interactions; metrics averaged over
1,000 seeded test users (`--max-users 1000`, seed 42) for runtime. Raw output:
`experiments/ablation_results.csv`. Figures: `reports/figures/{p,r,ndcg}_at_10.png`.

## Results (K=10)

| Model | P@10 | R@10 | NDCG@10 | HR@10 |
|---|---|---|---|---|
| Baseline | 0.0001 | 0.00014 | 0.00029 | 0.001 |
| Baseline + Temporal | 0.0001 | 0.00014 | 0.00030 | 0.001 |
| Baseline + Aspect | 0.0002 | 0.00064 | 0.00095 | 0.002 |
| Full (both) | 0.0002 | 0.00064 | 0.00095 | 0.002 |

(K=5 shows the same ordering; see CSV.)

## Observations (honest)

- Absolute values are very low: exact-hit prediction over 522K recipes from sparse
  histories is an extremely hard task, and HR@10 ≈ 0.1–0.2% reflects that.
- **Review-aspect signals double hit-rate vs baseline** (0.002 vs 0.001) and improve
  NDCG — the "why" behind ratings carries the most added value.
- **Temporal re-weighting alone is neutral** on this protocol: recent-preference
  TF-IDF overlap does not re-rank the baseline's top candidates enough to surface
  held-out items. It still powers the shift score and explanations in the UI.
- Full model matches aspect-only here: with default weights (0.5/0.25/0.25) the
  temporal part adds no further ranking gain on these users. Weight tuning
  (see `.env`: `W_BASELINE/W_TEMPORAL/W_ASPECT`, `TEMPORAL_LAMBDA`) is the
  natural next experiment — no claim beyond the measured numbers is made.
