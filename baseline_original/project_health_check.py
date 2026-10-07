import os
import pandas as pd
from joblib import load
import pickle

def check_project_status():
    print("🔍 CHECKING PROJECT STATUS")
    print("=" * 50)
    
    # Check required directories
    dirs_to_check = [
        "data/processed",
        "data/code/datasets", 
        "models",
        "reports"
    ]
    
    for dir_path in dirs_to_check:
        if os.path.exists(dir_path):
            print(f"✅ Directory exists: {dir_path}")
        else:
            print(f"❌ Missing directory: {dir_path}")
    
    print("\n📁 CHECKING REQUIRED FILES")
    print("=" * 30)
    
    # Check required data files
    required_files = {
        "Raw Data": [
            "data/code/datasets/RAW_recipes.csv",
            "data/code/datasets/RAW_interactions.csv"
        ],
        "Processed Data": [
            "data/processed/recipes_processed.csv",
            "data/processed/cf_interactions.csv",
            "data/processed/interactions_processed.csv"
        ],
        "Models": [
            "models/recommendation_models.joblib",
            "models/clustering_model.joblib"
        ],
        "Cache": [
            "data/processed/data_cache.pkl"
        ]
    }
    
    for category, files in required_files.items():
        print(f"\n{category}:")
        for file_path in files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path) / (1024*1024)  # MB
                print(f"  ✅ {file_path} ({size:.1f} MB)")
            else:
                print(f"  ❌ {file_path}")
    
    print("\n🤖 CHECKING MODELS")
    print("=" * 20)
    
    # Check models
    try:
        models = load("models/recommendation_models.joblib")
        print(f"✅ Recommendation models loaded: {list(models.keys())}")
        if 'svd_model' in models:
            print(f"  📊 SVD model type: {type(models['svd_model'])}")
        if 'tfidf_vectorizer' in models:
            print(f"  📝 TF-IDF vectorizer type: {type(models['tfidf_vectorizer'])}")
    except Exception as e:
        print(f"❌ Error loading recommendation models: {e}")
    
    try:
        clustering = load("models/clustering_model.joblib")
        print(f"✅ Clustering model loaded: {list(clustering.keys())}")
    except Exception as e:
        print(f"❌ Error loading clustering model: {e}")
    
    print("\n📊 CHECKING DATA QUALITY")
    print("=" * 25)
    
    # Check processed data
    try:
        recipes_df = pd.read_csv("data/processed/recipes_processed.csv")
        print(f"✅ Recipes processed: {len(recipes_df)} recipes")
        print(f"  📝 Required columns present: {all(col in recipes_df.columns for col in ['id', 'name', 'content_features'])}")
        
        # Check for content_features
        if 'content_features' in recipes_df.columns:
            non_empty_content = recipes_df['content_features'].notna().sum()
            print(f"  📄 Non-empty content_features: {non_empty_content}/{len(recipes_df)}")
        
    except Exception as e:
        print(f"❌ Error checking recipes data: {e}")
    
    try:
        interactions_df = pd.read_csv("data/processed/cf_interactions.csv")
        print(f"✅ CF Interactions: {len(interactions_df)} interactions")
        unique_users = interactions_df['user_id'].nunique()
        unique_recipes = interactions_df['recipe_id'].nunique()
        print(f"  👥 Unique users: {unique_users}")
        print(f"  🍳 Unique recipes: {unique_recipes}")
    except Exception as e:
        print(f"❌ Error checking interactions data: {e}")
    
    print("\n🧪 TESTING CORE FUNCTIONALITY")
    print("=" * 30)
    
    # Test imports
    try:
        from data.Scripts.recommender_app import load_and_prepare_data
        print("✅ Can import recommender_app functions")
    except Exception as e:
        print(f"❌ Import error: {e}")
    
    # Test data loading
    try:
        if os.path.exists("data/processed/data_cache.pkl"):
            with open("data/processed/data_cache.pkl", 'rb') as f:
                cache = pickle.load(f)
            print(f"✅ Data cache loaded: {list(cache.keys())}")
        else:
            print("ℹ️  No data cache found (will be created on first run)")
    except Exception as e:
        print(f"❌ Error loading cache: {e}")

if __name__ == "__main__":
    check_project_status()
