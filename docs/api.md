# API reference (product + research)

Auth: `POST /api/auth/register|login|refresh`, `GET /api/auth/me`
Profile: `GET|PUT /api/profile`, `POST /api/profile/password`,
`GET|PUT /api/preferences`
Taste: `GET /api/home[?intent=]`, `GET /api/taste`, `GET /api/taste/evolution`
Recipes: `GET /api/recipes[?q&limit&offset]`, `GET /api/recipes/{id}`,
`GET /api/recipes/search?q&mode=keyword|hybrid[&max_minutes&diet&min_protein&max_calories]`,
`GET /api/recipes/semantic-search`, `GET /api/discover`
Actions: `POST /api/interactions/{id}` (LIKE/DISLIKE/SAVE/UNSAVE/COOKED/RATED/REVIEW),
`GET /api/favorites`, `GET /api/interactions/mine`
Ingredients/pantry/cook: `/api/ingredients/lookup|info`, `/api/pantry[/items...]`,
`/api/cook/matches|missing|missing-to-shopping`
Meals/shopping: `/api/meal-plans[?week_start]`, `PUT .../slot`, `POST .../generate`,
`/api/shopping-list[...]` (+merge-duplicates, from-recipe, from-pantry, clear-completed)
Imports/collections/events: `/api/imports`, `/api/collections[/{id}[/items]]`,
`POST /api/events`, `POST /api/events/shown-batch`
Research (unchanged): `/api/recommendations/{uid}[?mode]`,
`/api/preferences/{uid}[/evolution|/aspects]`, `/api/demo_users`,
`/api/dataset/status`, `/api/research/summary`, `/api/health`

Conventions: JWT Bearer; 401 unauthenticated; 404 unknown ids + cross-user
objects (no existence oracle); 422 validation; 429 auth backstop. All
user-owned routes scope by `current_user_id`. Every frontend `api()` call is
covered by `tests/test_contract.py`.
