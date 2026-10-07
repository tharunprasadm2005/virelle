# Methodology

1. **Collection**: real Food.com Recipes & Reviews (Kaggle `irkaal/foodcom-recipes-and-reviews`) → `data/raw/`.
2. **Validation**: `schema.py` normalises headers, accepts variants, errors clearly on missing columns.
3. **Preprocessing**: dedup keep-last; drop rating 0; missing review→""; missing date→user/global median;
   invalid recipe_ids dropped; nutrition coerced; activity filter (≥5/user, ≥3/recipe; skipped only if it would empty the frame).
4. **Baseline**: TF-IDF content + TruncatedSVD CF, hybrid 0.7/0.3 (preserved from `baseline_original/`;
   surprise→SVD swap is same model family, portability-motivated).
5. **Aspect extraction** (`aspect_model.py`): curated lexicon (17 aspects) + sentiment window with negation
   and "too/overly" handling → per-review signed scores → mean-aggregated user/recipe profiles → cosine compatibility.
6. **Temporal modelling** (`temporal.py`): chronological sort; exp-decay (default λ=0.02) or window weights;
   old/recent split (60/40); shift = cosine distance of TF-IDF mean vectors; adaptive text weights recent higher.
7. **Adaptive ranking**: normalised `w1·baseline + w2·temporal + w3·aspect` (default 0.5/0.25/0.25, validated sum=1).
8. **Evaluation**: per-user temporal split (train older / test recent liked, rating≥4); P@K/R@K/NDCG@K/HR@K;
   4-way ablation. **All metrics from real data only** — no synthetic data in this path.
