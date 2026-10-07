"""TEST FIXTURE — NOT PROJECT DATA. Tiny synthetic frame for unit tests only.
Never used for training, evaluation claims, screenshots, or conclusions.
Real results always come from the Food.com dataset in data/raw/."""
import pandas as pd


def tiny_recipes():
    return pd.DataFrame([
        {"recipe_id": 1, "name": "Veggie Salad", "ingredients": ["lettuce", "tomato", "olive oil"],
         "tags": ["healthy", "salad", "quick"], "minutes": 10, "description": "fresh light healthy salad"},
        {"recipe_id": 2, "name": "Spicy Chicken Curry", "ingredients": ["chicken", "chili", "oil"],
         "tags": ["spicy", "indian", "dinner"], "minutes": 45, "description": "hot spicy chicken curry"},
        {"recipe_id": 3, "name": "Chocolate Cake", "ingredients": ["flour", "sugar", "butter"],
         "tags": ["sweet", "dessert", "baking"], "minutes": 60, "description": "sweet delicious cake"},
        {"recipe_id": 4, "name": "Quick Oatmeal", "ingredients": ["oats", "milk", "honey"],
         "tags": ["healthy", "quick", "breakfast"], "minutes": 5, "description": "easy quick healthy breakfast"},
        {"recipe_id": 5, "name": "Greasy Burger", "ingredients": ["beef", "cheese", "oil"],
         "tags": ["fast-food", "heavy"], "minutes": 20, "description": "heavy oily burger"},
        {"recipe_id": 6, "name": "Lentil Soup", "ingredients": ["lentils", "carrot", "onion"],
         "tags": ["healthy", "soup", "vegan"], "minutes": 35, "description": "light healthy soup easy"},
    ])


def tiny_interactions():
    rows = [
        (1, 2, 5, "The chicken curry was tasty but too spicy and oily.", "2018-03-01"),
        (1, 5, 4, "Heavy and greasy but tasty.", "2018-06-15"),
        (1, 3, 5, "Delicious sweet cake, loved it.", "2019-01-10"),
        (1, 1, 5, "Fresh healthy and light salad, very easy and quick.", "2021-05-01"),
        (1, 4, 5, "Quick easy healthy breakfast, light and fresh.", "2021-08-20"),
        (1, 6, 4, "Healthy light soup, easy to prepare.", "2021-11-11"),
        (2, 2, 5, "Amazing spicy flavor, loved the heat.", "2021-02-02"),
        (2, 5, 5, "Great burger, quick and tasty.", "2021-04-04"),
        (2, 3, 2, "Too sweet for me.", "2021-06-06"),
    ]
    return pd.DataFrame([{"user_id": u, "recipe_id": r, "rating": rt, "review": rv, "date": d}
                         for u, r, rt, rv, d in rows])
