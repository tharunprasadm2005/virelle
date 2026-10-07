# Models Directory

This directory contains trained machine learning models:

- `recommendation_models.joblib`: Contains SVD model and TF-IDF vectorizer
- `clustering_model.joblib`: K-Means clustering model for recipe categorization

## Model Details

### SVD Model
- Collaborative filtering model trained using scikit-surprise
- Used for generating user-based recommendations

### TF-IDF Vectorizer
- Content-based filtering model
- Vectorizes recipe text features for similarity calculations

### Clustering Model
- K-Means clustering for recipe categorization
- Groups similar recipes for improved recommendations

## Note
Model files are not tracked in git due to size constraints. 
Run preprocessing script to generate these models.
