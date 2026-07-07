from schema import create_schema
from seed import seed
from database import fetch_df, insert_row, row_exists
from recipe_engine import generate_candidates, build_recipe_from_candidate

create_schema()
seed()
assert fetch_df('SELECT name FROM sqlite_master WHERE type="table" AND name="ingredient_aliases"').shape[0] == 1
candidates = generate_candidates('Chicken', 'Swiss Chard', 'Rice', 'Comfort Food', 'Low', 'Budget', 30, 4, 10)
assert candidates
recipe = build_recipe_from_candidate(candidates[0])
assert recipe['instructions']
print('Smoke test passed: schema, seed, alias table, candidates, recipe generation.')
