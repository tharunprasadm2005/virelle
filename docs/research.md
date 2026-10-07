# Research preservation (academic engine vs product ranking)

## Academic engine (frozen logic, reproducible)
`src/recommender/{baseline,temporal,aspect_model,hybrid,explanations,evaluate}.py`
+ `scripts/` + `experiments/ablation_results.csv`. Measured on real Food.com
(per-user temporal split): baseline HR@10 0.001, +temporal 0.001 (neutral —
reported as measured, no improvement claimed), +aspect 0.002, full 0.002.
`baseline_original/` untouched. Research endpoints unchanged.

## Product ranking layer (separate by design)
Home/cook/search fusion (`COOK_W_*`, `SEARCH_W_*`, nutrition boosts, fatigue
penalties, intent) lives in `backend/app/api/*` + `src/ingredients/*` + taste
bridge. It REUSES engine pieces (CB scores, aspect compatibility, temporal
profiles) but never alters them. Product changes are NOT academic claims and
are never folded into `experiments/` unless a phase explicitly re-runs
evaluation with a documented protocol change (none has).
