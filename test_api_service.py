from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from api_service import (
    APIContractError,
    _candidate_view,
    get_recipe,
    get_recipe_list,
    normalize_kitchen_snapshot,
    save_my_kitchen,
)
from household_inventory import bootstrap_local_household, get_household_inventory


def kitchen_payload():
    return {
        "household_id": "local-demo-household",
        "servings": 4,
        "energy": "Low",
        "inventory": [
            {
                "name": "Chicken breast",
                "storage": "Freezer",
                "form": "Frozen Raw",
                "amount": "little",
                "quantity_band": 1,
            },
            {
                "name": "White rice",
                "storage": "Pantry",
                "form": "Dry",
                "amount": "plenty",
                "quantity_band": 3,
            },
            {
                "name": "Mushrooms",
                "storage": "Fresh",
                "form": "Fresh Raw",
                "amount": "little",
                "quantity_band": 1,
            },
        ],
    }


def diverse_kitchen_payload():
    return {
        "household_id": "local-demo-household",
        "servings": 4,
        "energy": "Low",
        "inventory": [
            {"name": "Canned chicken", "form": "Canned", "amount": "little"},
            {"name": "White rice", "form": "Dry", "amount": "plenty"},
            {"name": "White beans", "form": "Canned", "amount": "little"},
            {"name": "Chicken broth", "form": "Canned", "amount": "little"},
            {"name": "Eggs", "form": "Fresh Raw", "amount": "plenty"},
            {"name": "Cheese", "form": "Fresh", "amount": "little"},
            {"name": "Chicken breast", "form": "Frozen Raw", "amount": "plenty"},
            {"name": "Onions", "form": "Fresh Raw", "amount": "plenty"},
            {"name": "Carrots", "form": "Fresh Raw", "amount": "plenty"},
        ],
    }


class APIServiceTests(unittest.TestCase):
    def test_snapshot_normalizes_current_browser_payload(self):
        snapshot = normalize_kitchen_snapshot(kitchen_payload())
        self.assertEqual(snapshot["api_version"], "1.0")
        self.assertEqual(
            [item["quantity_band"] for item in snapshot["inventory_lots"]],
            ["a_little", "plenty", "a_little"],
        )
        self.assertEqual(snapshot["inventory_lots"][0]["storage_location"], "Freezer")

    def test_recipe_list_exposes_additive_v1_fields(self):
        response = get_recipe_list(kitchen_payload())
        self.assertEqual(response["api_version"], "1.0")
        self.assertTrue(response["candidates"])
        self.assertEqual(response["recipes"], response["candidates"])
        first = response["candidates"][0]
        for field in (
            "candidate_id", "meal_shape", "serving_temperature",
            "preparation_mode", "capability_status", "cost_estimate",
        ):
            self.assertIn(field, first)
        self.assertEqual(first["serving_temperature"], "hot")
        self.assertEqual(first["preparation_mode"], "cooked")
        self.assertIsNone(first["cost_estimate"])

    def test_recipe_round_trip_uses_deterministic_candidate_id(self):
        candidates = get_recipe_list(kitchen_payload())["candidates"]
        recipe = get_recipe({
            "candidate_id": candidates[0]["candidate_id"],
            "kitchen": kitchen_payload(),
        })
        self.assertEqual(recipe["candidate_id"], candidates[0]["candidate_id"])
        self.assertTrue(recipe["steps"])
        self.assertIn("Chicken breast — Frozen Raw", recipe["ingredients"])
        self.assertEqual(recipe["capability_status"], "supported")

    def test_recipe_list_builds_distinct_meal_concepts_not_one_bundle_in_forms(self):
        candidates = get_recipe_list(diverse_kitchen_payload())["candidates"]

        self.assertGreaterEqual(len(candidates), 4)
        self.assertEqual(len({item["candidate_id"] for item in candidates}), len(candidates))
        self.assertGreaterEqual(
            len({item["candidate_id"].rsplit("-", 1)[0] for item in candidates}),
            3,
        )
        self.assertFalse(any(item["candidate_id"].startswith("cold-meal") for item in candidates))
        self.assertTrue(all("Comfort Food" not in item["title"] for item in candidates))

    def test_opened_recipe_lists_only_its_selected_components(self):
        kitchen = diverse_kitchen_payload()
        candidate = get_recipe_list(kitchen)["candidates"][0]

        recipe = get_recipe({"candidate_id": candidate["candidate_id"], "kitchen": kitchen})

        self.assertFalse(any(item.startswith("White beans") for item in recipe["ingredients"]))
        self.assertFalse(any(item.startswith("Cheese") for item in recipe["ingredients"]))
        self.assertFalse(any(item.startswith("Eggs") for item in recipe["ingredients"]))

        soup = next(item for item in get_recipe_list(kitchen)["candidates"] if item["meal_shape"] == "soup")
        soup_recipe = get_recipe({"candidate_id": soup["candidate_id"], "kitchen": kitchen})
        self.assertTrue(any(item.startswith("Chicken broth") for item in soup_recipe["ingredients"]))

    def test_opened_recipe_includes_forms_and_complete_seasoning(self):
        kitchen = diverse_kitchen_payload()
        kitchen["equipment"] = [{"name": "Microwave"}]
        candidate = next(
            item for item in get_recipe_list(kitchen)["candidates"]
            if item["candidate_id"].startswith("skillet-chicken-breast")
        )

        recipe = get_recipe({"candidate_id": candidate["candidate_id"], "kitchen": kitchen})

        self.assertIn("Chicken breast — Frozen Raw", recipe["ingredients"])
        self.assertIn("Onions — Fresh Raw", recipe["ingredients"])
        self.assertIn("Carrots — Fresh Raw", recipe["ingredients"])
        self.assertIn("Garlic powder — 1/2 teaspoon", recipe["ingredients"])
        self.assertIn("Black pepper — 1/4 teaspoon", recipe["ingredients"])
        self.assertEqual(
            len(recipe["ingredients"]),
            len({item.split(" — ", 1)[0].lower() for item in recipe["ingredients"]}),
        )
        later_steps = " ".join(recipe["steps"][4:]).lower()
        self.assertNotIn("frozen chicken", later_steps)
        self.assertNotIn("the foundation", " ".join(recipe["steps"]).lower())
        self.assertEqual(
            1,
            sum("main cooking is done" in step.lower() for step in recipe["steps"]),
        )

    def test_candidate_temperature_and_preparation_follow_the_method(self):
        cold = _candidate_view({"strategy": "cold_meal", "candidate_id": "cold-1"})

        self.assertEqual(cold["serving_temperature"], "cold")
        self.assertEqual(cold["preparation_mode"], "assembled")

    def test_cost_filter_is_reserved_but_does_not_change_culinary_generation(self):
        payload = kitchen_payload()
        payload["cost_filter"] = {
            "cost_view": "shop_today", "maximum_total": 25, "currency": "USD"
        }
        with patch("api_service.generate_candidates", return_value=[]) as generate:
            response = get_recipe_list(payload)
        self.assertEqual(generate.call_args.kwargs["budget_level"], "Moderate")
        self.assertIn(
            "cost_estimate_unavailable",
            {notice["code"] for notice in response["notices"]},
        )

    def test_unknown_candidate_is_rejected(self):
        with self.assertRaises(APIContractError):
            get_recipe({"candidate_id": "not-real", "kitchen": kitchen_payload()})

    def test_save_kitchen_resolves_names_and_preserves_quantity_band(self):
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "api.db"
            with closing(sqlite3.connect(db_path)) as con:
                with con:
                    con.executescript("""
                        CREATE TABLE users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, display_name TEXT NOT NULL, default_servings INTEGER, leftovers_ok INTEGER);
                        CREATE TABLE ingredients (ingredient_id INTEGER PRIMARY KEY, name TEXT, category TEXT);
                        CREATE TABLE ingredient_aliases (alias_id INTEGER PRIMARY KEY, ingredient_id INTEGER, alias_name TEXT);
                        CREATE TABLE ingredient_forms (form_id INTEGER PRIMARY KEY, ingredient_id INTEGER, form_name TEXT);
                        CREATE TABLE user_inventory (inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,ingredient_id INTEGER,form_id INTEGER,prep_id INTEGER,quantity REAL,unit TEXT,storage_location TEXT,expiration_date TEXT,confidence_level TEXT);
                        CREATE TABLE foundations (foundation_id INTEGER PRIMARY KEY, name TEXT);
                    """)
                    con.execute("INSERT INTO ingredients VALUES (1,'Chicken breast','Chicken')")
                    con.execute("INSERT INTO ingredient_forms VALUES (10,1,'Frozen Raw')")
            user_id, household_id = bootstrap_local_household(db_path)
            payload = {
                "household_id": household_id,
                "inventory": [{
                    "name": "Chicken breast", "form": "Frozen Raw",
                    "storage": "Freezer", "amount": "little",
                }],
            }
            result = save_my_kitchen(
                payload, household_id=household_id, acting_user_id=user_id,
                db_path=db_path,
            )
            self.assertEqual(result["saved_inventory_lots"], 1)
            loaded = get_household_inventory(db_path, household_id, user_id)
            self.assertEqual(loaded[0]["quantity_band"], "a_little")
            self.assertEqual(loaded[0]["origin"], "manual")


if __name__ == "__main__":
    unittest.main()
