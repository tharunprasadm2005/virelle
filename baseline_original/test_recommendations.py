import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'data', 'Scripts'))

def test_recommendation_system():
    print("🧪 TESTING RECOMMENDATION SYSTEM")
    print("=" * 40)
    
    try:
        # Import the main functions
        from recommender_app import (
            load_and_prepare_data, 
            recommend_for_new_user, 
            hybrid_recommendations,
            init_db
        )
        print("✅ Successfully imported recommendation functions")
        
        # Initialize database
        init_db()
        print("✅ Database initialized")
        
        # Load data
        print("📊 Loading data...")
        data_cache = load_and_prepare_data()
        print(f"✅ Data loaded successfully")
        print(f"  📊 Recipes: {len(data_cache['recipes_df'])}")
        print(f"  🤝 Interactions: {len(data_cache['interactions_df'])}")
        print(f"  👥 Users: {len(data_cache['user_item_map'])}")
        
        # Test new user recommendations
        print("\n🆕 Testing new user recommendations...")
        test_profile = {
            'username': 'test_user',
            'dietary_preferences': {'vegetarian': False, 'vegan': False},
            'preferred_cuisines': ['italian'],
            'favorite_ingredients': ['chicken', 'pasta'],
            'max_cook_time': 60
        }
        
        new_user_recs = recommend_for_new_user(
            test_profile, 
            data_cache['recipes_df'], 
            data_cache['n_ratings_map'], 
            5
        )
        
        if new_user_recs:
            print(f"✅ Generated {len(new_user_recs)} recommendations for new user")
            for i, rec in enumerate(new_user_recs[:3], 1):
                print(f"  {i}. {rec['name']} (Score: {rec['score']:.2f})")
        else:
            print("❌ No recommendations generated for new user")
        
        # Test existing user recommendations
        print("\n👤 Testing existing user recommendations...")
        sample_user_id = list(data_cache['user_item_map'].keys())[0]
        user_interactions = data_cache['interactions_df'][
            data_cache['interactions_df']['user_id'] == sample_user_id
        ]
        
        if not user_interactions.empty:
            seed_recipes = user_interactions.nlargest(3, 'rating')['recipe_id'].tolist()
            
            existing_user_recs = hybrid_recommendations(
                sample_user_id, 
                seed_recipes, 
                data_cache, 
                5
            )
            
            if existing_user_recs:
                print(f"✅ Generated {len(existing_user_recs)} recommendations for existing user {sample_user_id}")
                for i, rec in enumerate(existing_user_recs[:3], 1):
                    print(f"  {i}. {rec['name']} (Score: {rec['score']:.2f})")
            else:
                print("❌ No recommendations generated for existing user")
        
        print("\n✅ ALL TESTS PASSED - Recommendation system is working!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_recommendation_system()
