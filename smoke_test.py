from schema import create_schema
from seed import seed
from database import fetch_df
from recipe_engine import generate_candidates, build_recipe_from_candidate


create_schema()
seed()

assert fetch_df(
    'SELECT name FROM sqlite_master '
    'WHERE type="table" AND name="ingredient_aliases"'
).shape[0] == 1

candidates = generate_candidates(
    "Chicken breast",
    "Swiss chard",
    "Rice",
    "Chinese",
    "Low",
    "Budget",
    45,
    4,
    10,
    vegetable_names=["Swiss chard", "Mushrooms", "Asparagus"],
)

assert candidates

candidate = candidates[0]

assert "opportunities" in candidate
assert candidate["opportunities"]
assert any(
    opportunity.get("opportunity_id") == "ko_dry_browning"
    for opportunity in candidate["opportunities"]
), candidate["opportunities"]

recipe = build_recipe_from_candidate(candidate)

assert recipe["instructions"]

print(
    "Smoke test passed: schema, seed, alias table, "
    "opportunity discovery, candidates, recipe generation."
)
