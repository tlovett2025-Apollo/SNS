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


def frozen_ground_beef_payload():
    return {
        "household_id": "local-demo-household",
        "servings": 4,
        "energy": "Low",
        "equipment": [
            {"name": "Microwave"},
            {"name": "Pressure cooker"},
            {"name": "Skillet"},
        ],
        "inventory": [
            {"name": "Ground beef", "form": "Frozen Raw", "amount": "plenty"},
            {"name": "Onions", "form": "Fresh", "amount": "plenty"},
            {"name": "White rice", "form": "Dry", "amount": "plenty"},
            {"name": "Chicken broth", "form": "Shelf-stable", "amount": "little"},
            {"name": "Milk", "form": "Refrigerated", "amount": "little"},
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

    def test_snapshot_preserves_exact_package_and_piece_counts_without_a_fuzzy_band(self):
        snapshot = normalize_kitchen_snapshot({
            "household_id": "local-demo-household",
            "inventory": [
                {"name": "White beans", "form": "Canned", "quantity": 3, "unit": "can"},
                {"name": "Lasagna noodles", "form": "Dry", "quantity": 8, "unit": "noodle"},
            ],
        })

        self.assertEqual(
            [(item["quantity"], item["unit"], item["quantity_band"]) for item in snapshot["inventory_lots"]],
            [(3.0, "can", None), (8.0, "noodle", None)],
        )

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
        provenance = recipe["build_provenance"]
        self.assertRegex(provenance["build_id"], r"^SNS-[0-9a-f]{12}$")
        self.assertEqual(provenance["configuration"]["candidate_id"], candidates[0]["candidate_id"])
        self.assertTrue(any(item["path"] == "cooking_planner.py" for item in provenance["files"]))

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

    def test_numbered_plan_contains_actions_and_handles_frozen_ground_beef(self):
        kitchen = frozen_ground_beef_payload()
        candidate = get_recipe_list(kitchen)["candidates"][0]

        recipe = get_recipe({"candidate_id": candidate["candidate_id"], "kitchen": kitchen})
        plan = " ".join(recipe["steps"])
        all_statements = " ".join(item["text"] for item in recipe["plan_items"])

        self.assertIn("Ground beef — Frozen Raw", recipe["ingredients"])
        self.assertTrue(recipe["steps"][0].startswith("Minutes 0–2:"))
        self.assertIn("Measure the rice", recipe["steps"][0])
        self.assertNotIn("Tonight we are making", plan)
        self.assertNotIn("Plan on about", plan)
        self.assertNotIn("Gather the ingredients", plan)
        self.assertIn("Tonight we are making", all_statements)
        self.assertIn("Plan on about", all_statements)
        self.assertIn("gather the ingredients", all_statements)
        self.assertIn("microwave defrost setting", plan)
        self.assertIn("thawed ground beef", plan)
        self.assertIn("no pink ground meat remains", plan)
        self.assertIn("30 seconds after the last pink disappears", plan)
        self.assertNotIn("food thermometer", plan)
        self.assertIn("same skillet", plan)
        self.assertNotIn("Slice Ground beef", plan)
        self.assertIn("Prepare these first", plan)
        self.assertNotIn("While Ground beef thaws", plan)
        self.assertNotIn("ingredient prep is handled", plan.lower())
        self.assertEqual(1, sum("Prep is complete" in step for step in recipe["steps"]))
        self.assertEqual(1, sum("Now the cooking begins" in step for step in recipe["steps"]))
        self.assertLess(plan.index("microwave defrost setting"), plan.index("Heat the skillet"))

        kinds = [item["kind"] for item in recipe["plan_items"]]
        self.assertEqual(kinds[:4], ["info", "info", "info", "action"])
        self.assertTrue(any(
            item["kind"] == "info" and "come to pressure" in item["text"]
            for item in recipe["plan_items"]
        ))
        self.assertFalse(any(
            "come to pressure" in step for step in recipe["steps"]
        ))
        self.assertTrue(any(
            item["kind"] == "info"
            and "timing the defrosting" in item["text"]
            and "instead of sitting" in item["text"]
            for item in recipe["plan_items"]
        ))
        thaw_step = next(step for step in recipe["steps"] if "microwave defrost setting" in step)
        prep_step = next(step for step in recipe["steps"] if "finishes defrosting" in step)
        self.assertTrue(thaw_step.startswith("Minutes 15–22:"))
        self.assertTrue(prep_step.startswith("Minutes 19–21:"))
        self.assertIn("\n\n", prep_step)
        self.assertEqual(
            recipe["missing_items"],
            ["Cooking oil or butter", "Garlic powder", "Onion powder", "Black pepper", "Cornstarch"],
        )
        self.assertNotIn("Chicken broth", recipe["missing_items"])
        self.assertNotIn("Milk", recipe["missing_items"])
        self.assertNotIn("Cold water", recipe["missing_items"])
        self.assertNotIn("Salt", recipe["missing_items"])
        self.assertIn("Plate White rice", recipe["steps"][-1])
        self.assertEqual(recipe["plan_items"][-1], {
            "kind": "info", "text": "Nicely done. Dinner is ready.",
        })
        self.assertLess(plan.index("Taste before adding salt"), plan.index("Plate White rice"))

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
