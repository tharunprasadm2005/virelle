# Database (SQLite `tasteflow.db`; recipes stay in processed CSVs)

`users(id, name, email UNIQUE, password_hash, linked_foodcom_id, timestamps)` →
`user_preferences(user_id PK/FK, diet, cuisines/priorities/avoid/nutrition_goals JSON, max_minutes)` →
`user_recipe_interactions(FK users CASCADE, recipe_id, type CHECK, rating CHECK 1-5, review_text, created_at; idx user, recipe)` →
`meal_plans(UNIQUE(user,week))` → `meal_plan_items(FK CASCADE, day, slot CHECK, recipe_id NULL=empty, UNIQUE(plan,day,slot))` →
`shopping_items(FK CASCADE, label/category/quantity/checked/recipe_id; idx user)` →
`pantry_items(FK CASCADE, label/normalized/qty/unit/category/expiry/available; idx user)` →
`imported_recipes(FK CASCADE, attributed fields; idx user)` →
`collections(FK CASCADE, UNIQUE(user,name))` → `collection_items(FK CASCADE, recipe_id, source CHECK, UNIQUE(coll,recipe,source))` →
`recommendation_events(FK CASCADE, SHOWN|OPENED, context; idx user, recipe)` →
`schema_migrations(version PK)`.

Evolution: ordered SQL in `backend/app/migrations.py`, applied at startup (v1–v6).
No ORM by decision (single-node; revisit only on concurrent-writer need).
