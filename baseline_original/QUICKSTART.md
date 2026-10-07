# Quick Start Guide

## 1. Initial Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/DSProject1.git
cd DSProject1

# Run setup script
python setup.py
```

## 2. Prepare Your Data

Place your datasets in `data/code/datasets/`:
- `RAW_recipes.csv` - Recipe data
- `RAW_interactions.csv` - User interaction data

### Data Format Requirements

**RAW_recipes.csv** should contain:
- `id`: Recipe ID
- `name`: Recipe name  
- `ingredients`: Ingredients list (string format)
- `tags`: Recipe tags
- `nutrition`: Nutrition array
- `minutes`: Cook time
- `description`: Recipe description

**RAW_interactions.csv** should contain:
- `user_id`: User ID
- `recipe_id`: Recipe ID
- `rating`: Rating (1-5)
- `date`: Interaction date

## 3. Process Data and Train Models

```bash
python data/Scripts/preprocess_recipes_and_build_initial_models.py
```

## 4. Run the Recommendation System

```bash
python data/Scripts/recommender_app.py
```

## 5. Test the System

```bash
python test_recommendations.py
python project_health_check.py
```

## Need Sample Data?

If you don't have your own datasets, you can use public recipe datasets from:
- [Food.com Kaggle Dataset](https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions)
- [Recipe1M Dataset](http://pic2recipe.csail.mit.edu/)

Make sure to format the data according to the requirements above.
