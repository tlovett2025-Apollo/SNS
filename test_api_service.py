from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from datetime import date

from api_service import (
    APIContractError,
    _candidate_view,
    get_meal_builder_options,
    get_recipe,
    get_recipe_list,
    normalize_kitchen_snapshot,
    save_my_kitchen,
)
from household_inventory import bootstrap_local_household, get_household_inventory
from recipe_engine import build_recipe_from_candidate, generate_candidates


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


def cooked_bean_soup_payload(energy="Low", equipment=None):
    return {
        "household_id": "local-demo-household",
        "servings": 4,
        "energy": energy,
        "equipment": [{"name": name} for name in (equipment or ["Stovetop"])],
        "inventory": [
            {"name": "White beans", "form": "Cooked", "amount": "plenty"},
            {"name": "Carrots", "form": "Fresh Raw", "amount": "plenty"},
            {"name": "Chicken broth", "form": "Shelf-stable", "amount": "plenty"},
        ],
    }


class APIServiceTests(unittest.TestCase):
    def test_builder_braise_treats_kielbasa_as_a_supporting_protein(self):
        request = {
            "mode": "build_your_meal",
            "kitchen": {
                "inventory": [
                    {"name": "Beef broth", "form": "Shelf-stable", "amount": "plenty"},
                    {"name": "Garlic powder", "form": "Shelf-stable", "amount": "plenty"},
                    {"name": "Onion powder", "form": "Shelf-stable", "amount": "plenty"},
                    {"name": "Black pepper", "form": "Shelf-stable", "amount": "plenty"},
                ],
                "equipment": [{"name": "Stovetop"}],
            },
            "selections": {
                "proteins": [
                    {"name": "Beef brisket", "state": "Fresh Raw", "role": "main"},
                    {"name": "Kielbasa", "state": "Fresh Raw", "role": "supporting"},
                ],
                "produce": ["Limes"], "foundation": "",
                "extras": ["Ketchup", "Mustard", "BBQ sauce", "Hot sauce", "Worcestershire sauce"],
                "cuisine": "BBQ", "cooking_method": "skillet",
                "meal_structure": "integrated", "serving_temperature": "hot",
                "energy": "Low", "time_minutes": 240, "servings": 4,
            },
        }

        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})
        plan = " ".join(recipe["instructions"])

        self.assertTrue(any(line.startswith("Kielbasa — Fresh Raw · 1 piece") for line in recipe["ingredients"]))
        self.assertNotIn("KO-approved", plan)
        self.assertNotIn("thaw before browning", plan.lower())
        self.assertNotIn("Thaw Kielbasa", plan)
        self.assertNotIn("Plan on about", plan)
        self.assertIn("final", plan.lower())
        self.assertIn("Limes juice or wedges", plan)
        self.assertNotIn("distribute Kielbasa & Limes", plan)
        self.assertNotIn("Plate Limes", plan)
        self.assertIn("165°F for poultry sausage; 160°F for pork or beef sausage", plan)
        self.assertNotIn("Serve Ketchup & Mustard & BBQ sauce", plan)
        self.assertFalse(any("Shelf-stable" in line for line in recipe["ingredients"]))
        self.assertTrue(any(line.startswith("Beef brisket — Fresh Raw") for line in recipe["ingredients"]))
        self.assertLess(recipe["active_minutes"], 30)

    def test_chicken_tomato_spaghetti_uses_every_ingredient_and_names_two_vessels_honestly(self):
        request = {
            "mode": "build_your_meal",
            "kitchen": {
                "inventory": [
                    {"name": "Chicken breast", "form": "Fresh Raw", "quantity": 4, "unit": "piece"},
                    {"name": "Tomatoes", "form": "Fresh", "amount": "plenty"},
                    {"name": "Spaghetti", "form": "Dry", "amount": "plenty"},
                    {"name": "Butter", "form": "Refrigerated", "amount": "plenty"},
                    {"name": "Garlic powder", "form": "Shelf-stable", "amount": "plenty"},
                    {"name": "Onion powder", "form": "Shelf-stable", "amount": "plenty"},
                    {"name": "Black pepper", "form": "Shelf-stable", "amount": "plenty"},
                    {"name": "Chicken broth", "form": "Shelf-stable", "amount": "plenty"},
                    {"name": "Milk", "form": "Refrigerated", "amount": "plenty"},
                ],
                "equipment": [{"name": "Stovetop"}],
            },
            "selections": {
                "protein": "Chicken breast", "protein_state": "Fresh Raw",
                "produce": ["Tomatoes"], "foundation": "Spaghetti", "extras": ["Butter"],
                "cuisine": "Comfort Food", "cooking_method": "skillet",
                "meal_structure": "integrated", "serving_temperature": "hot",
                "energy": "Low", "time_minutes": 60, "servings": 4,
            },
        }

        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})
        plan = " ".join(recipe["steps"])

        self.assertIn("Skillet Supper", choice["title"])
        self.assertNotIn("One-Pot", choice["title"])
        self.assertIn("Heat Butter in the skillet", plan)
        self.assertIn("Season with Garlic powder & Onion powder & Black pepper", plan)
        self.assertNotIn("Thaw", plan)
        self.assertIn("reduce the heat to low", plan)
        self.assertIn("without letting the sauce boil", plan)
        self.assertIn("Slice the rested Chicken breast", plan)
        self.assertTrue(recipe["recipe_validation"]["production_ready"])

    def test_composed_plate_is_not_offered_when_one_chicken_breast_cannot_make_four_entrees(self):
        candidates = generate_candidates(
            "Chicken breast", "Tomatoes & Zucchini", "", "Comfort Food",
            "Low", "Budget", 60, 4, 10,
            vegetable_names=["Tomatoes", "Zucchini"], protein_state="Fresh Raw",
            available_items=["Chicken breast", "Tomatoes", "Zucchini"],
            inventory_lots=[{"name": "Chicken breast", "form": "Fresh Raw", "quantity": 1, "unit": "piece"}],
            meal_structure="composed_plate",
        )

        self.assertEqual(candidates, [])

    def test_builder_brisket_supports_planning_ahead_stovetop_braise(self):
        request = {
            "mode": "build_your_meal",
            "kitchen": {"inventory": [], "equipment": [{"name": "Stovetop"}]},
            "selections": {
                "proteins": [
                    {"name": "Beef brisket", "state": "Fresh Raw", "role": "main"},
                    {"name": "Kielbasa", "state": "Fresh Raw", "role": "supporting"},
                ],
                "foundation": "Pinto beans", "produce": [], "extras": [],
                "cuisine": "BBQ", "cooking_method": "skillet",
                "meal_structure": "integrated", "serving_temperature": "hot",
                "energy": "High", "time_minutes": 240, "servings": 4,
            },
        }

        choice = get_recipe_list(request)["candidates"][0]

        self.assertEqual(choice["cooking_method"], "braise")
        self.assertLessEqual(choice["total_minutes"], 240)
        self.assertIn("Braise", choice["title"])

    def test_builder_brisket_has_a_trained_oven_braise_route(self):
        request = {
            "mode": "build_your_meal",
            "kitchen": {"inventory": [], "equipment": [{"name": "Oven"}, {"name": "Stovetop"}]},
            "selections": {
                "protein": "Beef brisket", "protein_state": "Fresh Raw",
                "produce": ["Onions"], "foundation": "", "extras": ["Beef broth", "BBQ sauce"],
                "cuisine": "BBQ", "cooking_method": "casserole",
                "meal_structure": "integrated", "serving_temperature": "hot",
                "energy": "Low", "time_minutes": 360, "servings": 4,
            },
        }

        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})

        self.assertEqual(choice["cooking_method"], "oven_braise")
        self.assertIn("325°F oven", " ".join(recipe["steps"]))
        self.assertNotIn("Onions does not yet have", " ".join(recipe["instructions"]))

    def test_builder_brisket_explains_when_selected_time_is_too_short(self):
        request = {
            "mode": "build_your_meal",
            "kitchen": {"inventory": [], "equipment": [{"name": "Stovetop"}]},
            "selections": {
                "protein": "Beef brisket", "protein_state": "Fresh Raw",
                "foundation": "Pinto beans", "produce": [], "extras": [],
                "cuisine": "BBQ", "cooking_method": "soup",
                "meal_structure": "integrated", "serving_temperature": "hot",
                "energy": "High", "time_minutes": 90, "servings": 4,
            },
        }

        with self.assertRaisesRegex(APIContractError, "needs a little more time"):
            get_recipe_list(request)

    def test_brisket_bean_soup_stages_canned_beans_and_lime_at_the_finish(self):
        request = {
            "mode": "build_your_meal",
            "kitchen": {"inventory": [], "equipment": [{"name": "Stovetop"}]},
            "selections": {
                "protein": "Beef brisket", "protein_state": "Fresh Raw",
                "produce": ["Limes", "Onions"], "foundation": "Pinto beans",
                "extras": ["Beef broth"], "cuisine": "Mexican",
                "cooking_method": "soup", "meal_structure": "integrated",
                "serving_temperature": "hot", "energy": "Low",
                "time_minutes": 240, "servings": 4,
            },
        }

        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})
        actions = recipe["steps"]
        instructions = recipe["instructions"]
        simmer = next(step for step in instructions if "gently simmer for about" in step.lower())
        finish = next(step for step in actions if "Limes" in step and "finish" in step.lower())

        self.assertNotIn("Limes", simmer)
        self.assertNotIn("Pinto beans", simmer)
        self.assertIn("Pinto beans", " ".join(actions))
        self.assertIn("juice or wedges", finish)
        self.assertNotIn("KO tenderness", " ".join(recipe["instructions"]))
        self.assertNotIn("This pause keeps", " ".join(recipe["instructions"]))

    def test_soup_places_selected_sauces_before_the_long_simmer(self):
        request = {
            "mode": "build_your_meal",
            "kitchen": {"inventory": [], "equipment": [{"name": "Stovetop"}]},
            "selections": {
                "protein": "Beef stew meat", "protein_state": "Fresh Raw",
                "produce": ["Carrots", "Celery", "Onions", "Potatoes"],
                "foundation": "", "extras": [
                    "Beef broth", "Tomato sauce", "Soy sauce", "Worcestershire sauce",
                ],
                "cuisine": "Comfort Food", "cooking_method": "soup",
                "meal_structure": "integrated", "serving_temperature": "hot",
                "energy": "Low", "time_minutes": 240, "servings": 4,
            },
        }

        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})
        plan = " ".join(recipe["steps"])

        self.assertIn(
            "Tomato sauce & Soy sauce & Worcestershire sauce "
            "into the cooking liquid before the long simmer",
            plan,
        )
        self.assertNotIn("serve Soy sauce", plan)
        self.assertNotIn("as part of the soup and heat it through", plan)
        self.assertEqual(recipe["total_minutes"], 96)
        self.assertEqual(recipe["active_minutes"], 21)
        self.assertEqual(recipe["passive_minutes"], 75)

    def test_recipe_ingredients_include_practical_vegetable_amounts(self):
        request = {
            "mode": "build_your_meal",
            "kitchen": {"inventory": [], "equipment": [{"name": "Stovetop"}]},
            "selections": {
                "protein": "Beef stew meat", "protein_state": "Fresh Raw",
                "produce": ["Carrots", "Celery", "Onions", "Potatoes"],
                "foundation": "", "extras": ["Beef broth"],
                "cooking_method": "soup", "meal_structure": "integrated",
                "serving_temperature": "hot", "time_minutes": 240, "servings": 4,
            },
        }

        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})

        self.assertIn("Carrots — about 2 cups", recipe["ingredients"])
        self.assertIn("Celery — about 1 cup", recipe["ingredients"])
        self.assertIn("Onions — about 1 cup", recipe["ingredients"])
        self.assertIn("Potatoes — about 2 cups", recipe["ingredients"])

    def test_builder_catalog_marks_current_kitchen_ownership(self):
        options = get_meal_builder_options(kitchen_payload())
        proteins = {item["name"]: item["owned"] for item in options["proteins"]}
        produce = {item["name"]: item["owned"] for item in options["produce"]}

        self.assertTrue(proteins["Chicken breast"])
        self.assertFalse(proteins["Ground beef"])
        self.assertTrue(produce["Mushrooms"])
        self.assertIn("Mayonnaise", {item["name"] for item in options["extras"]})
        self.assertIn("Salsa", {item["name"] for item in options["extras"]})
        self.assertIn("fruit", {item["kind"] for item in options["produce"]})
        self.assertFalse(next(item for item in options["serving_temperatures"] if item["id"] == "cold")["available"])

    def test_builder_returns_one_exact_method_and_preserves_shopping_needs(self):
        kitchen = kitchen_payload()
        request = {
            "mode": "build_your_meal",
            "kitchen": kitchen,
            "selections": {
                "protein": "Chicken breast",
                "protein_state": "Frozen Raw",
                "produce": ["Mushrooms", "Onions"],
                "foundation": "White rice",
                "extras": ["Mayonnaise", "Salsa"],
                "cuisine": "Comfort Food",
                "cooking_method": "skillet",
                "serving_temperature": "hot",
                "meal_occasion": "Dinner",
                "energy": "Low",
                "time_minutes": 60,
                "servings": 4,
            },
        }

        choices = get_recipe_list(request)["candidates"]
        self.assertEqual(len(choices), 1)
        self.assertTrue(choices[0]["candidate_id"].startswith("build-integrated-skillet-"))
        recipe = get_recipe({"candidate_id": choices[0]["candidate_id"], "kitchen": request})
        requirements = {
            item["name"]: item["status"] for item in recipe["inventory_requirements"]
        }
        self.assertEqual(requirements["Chicken breast"], "Have")
        self.assertEqual(requirements["Mushrooms"], "Have")
        self.assertEqual(requirements["Onions"], "Need")
        self.assertEqual(requirements["Mayonnaise"], "Need")
        self.assertEqual(requirements["Salsa"], "Need")
        self.assertIn("Onions", recipe["missing_items"])
        self.assertTrue(any("Mayonnaise" in step and "Salsa" in step for step in recipe["steps"]))

    def test_builder_multiple_proteins_keep_main_and_accent_roles(self):
        kitchen = kitchen_payload()
        request = {
            "mode": "build_your_meal",
            "kitchen": kitchen,
            "selections": {
                "proteins": [
                    {"name": "Chicken breast", "state": "Frozen Raw", "role": "main"},
                    {"name": "Bacon", "state": "Fresh Raw", "role": "accent"},
                ],
                "produce": ["Mushrooms"],
                "foundation": "White rice",
                "cooking_method": "skillet",
                "meal_structure": "layered_bowl",
                "serving_temperature": "hot",
                "time_minutes": 60,
                "servings": 4,
            },
        }

        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})
        plan = " ".join(recipe["steps"])

        self.assertEqual([item["role"] for item in choice["proteins"]], ["main", "accent"])
        self.assertIn("Chicken breast, Bacon", choice["title"])
        self.assertTrue(any(line.startswith("Bacon — Fresh Raw") for line in recipe["ingredients"]))
        self.assertIn("Cook Bacon first", plan)
        self.assertLess(plan.index("Cook Bacon first"), plan.index("Brown Chicken breast"))

    def test_grill_is_equipment_gated_and_uses_ko_grill_science(self):
        without_grill = get_meal_builder_options({"inventory": [], "equipment": []})
        with_grill_kitchen = {
            "inventory": [], "equipment": [{"name": "Outdoor Grill"}],
        }
        with_grill = get_meal_builder_options(with_grill_kitchen)
        self.assertFalse(next(item for item in without_grill["methods"] if item["id"] == "grill")["available"])
        self.assertTrue(next(item for item in with_grill["methods"] if item["id"] == "grill")["available"])

        request = {
            "mode": "build_your_meal", "kitchen": with_grill_kitchen,
            "selections": {
                "protein": "Chicken breast", "protein_state": "Fresh Raw",
                "produce": ["Tomatoes", "Zucchini"], "foundation": "",
                "cooking_method": "grill", "meal_structure": "composed_plate",
                "serving_temperature": "hot", "time_minutes": 45, "servings": 4,
            },
        }
        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})
        plan = " ".join(recipe["steps"])
        self.assertEqual(choice["heat_source"], "grill")
        self.assertIn("indirect heat", plan)
        self.assertIn("165°F", plan)
        self.assertIn("Grill Tomatoes cut-side down", plan)
        self.assertIn("still hold their shape", plan)
        self.assertIn("grill basket", plan)
        self.assertNotIn("scrape up the browned flavor", plan)

    def test_layered_bowl_tomatoes_remain_distinct_instead_of_becoming_sauce(self):
        request = {
            "mode": "build_your_meal",
            "kitchen": kitchen_payload(),
            "selections": {
                "protein": "Chicken breast",
                "protein_state": "Frozen Raw",
                "produce": ["Tomatoes"],
                "foundation": "White rice",
                "cooking_method": "skillet",
                "meal_structure": "layered_bowl",
                "serving_temperature": "hot",
                "time_minutes": 60,
                "servings": 4,
            },
        }

        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})
        plan = " ".join(recipe["steps"])

        self.assertIn("Keep Tomatoes distinct", plan)
        self.assertIn("stop before its pieces collapse into a sauce", plan)
        self.assertNotIn("Add Tomatoes to the skillet and cook until ready", plan)

    def test_builder_recognizes_custom_mayo_and_salsa_as_owned_extras(self):
        kitchen = kitchen_payload()
        kitchen["inventory"].extend([
            {"name": "Mayo", "form": "Refrigerated", "amount": "little"},
            {"name": "Salsa", "form": "Refrigerated", "amount": "little"},
        ])
        options = get_meal_builder_options(kitchen)
        extras = {item["name"]: item["owned"] for item in options["extras"]}

        self.assertTrue(extras["Mayonnaise"])
        self.assertTrue(extras["Salsa"])

    def test_builder_inherits_canned_and_ready_to_eat_forms_from_my_kitchen(self):
        kitchen = {
            "household_id": "forms-household",
            "inventory": [
                {"name": "Rotisserie chicken", "form": "Ready to Eat", "amount": "little"},
                {"name": "Navy beans", "form": "Canned", "amount": "little"},
                {"name": "Mushrooms", "form": "Fresh", "amount": "little"},
            ],
            "meal_preferences": {},
        }
        request = {
            "mode": "build_your_meal",
            "kitchen": kitchen,
            "selections": {
                "protein": "Rotisserie chicken",
                # The stale browser value must lose to the owned inventory lot.
                "protein_state": "Fresh Raw",
                "produce": ["Mushrooms"],
                "foundation": "Navy beans",
                "cooking_method": "skillet",
                "meal_structure": "integrated",
                "serving_temperature": "hot",
            },
        }
        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})
        plan = " ".join(recipe["steps"])

        self.assertIn("Rotisserie chicken — Cooked", recipe["ingredients"])
        self.assertTrue(any(line.startswith("Navy beans — Canned") for line in recipe["ingredients"]))
        self.assertIn("Drain and rinse Navy beans", plan)
        self.assertIn("slice or shred it as the meal needs", plan)
        self.assertIn("do not recook it", plan)
        self.assertNotIn("Rotisserie chicken to the skillet and cook until ready", plan)
        self.assertNotIn("Prep is complete", plan)
        self.assertNotIn("Now the cooking begins", plan)
        self.assertNotIn("main cooking is done", plan)

    def test_builder_classifies_composed_plate_and_layered_bowl_separately(self):
        kitchen = kitchen_payload()
        base = {
            "protein": "Chicken breast", "protein_state": "Frozen Raw",
            "produce": ["Mushrooms"], "foundation": "White rice",
            "cooking_method": "skillet", "serving_temperature": "hot",
        }
        for structure, expected_shape, expected_production in (
            ("composed_plate", "plate", "multi_component"),
            ("layered_bowl", "bowl", "component_assembly"),
        ):
            request = {
                "mode": "build_your_meal", "kitchen": kitchen,
                "selections": {**base, "meal_structure": structure},
            }
            choice = get_recipe_list(request)["candidates"][0]
            self.assertEqual(choice["meal_structure"], structure)
            self.assertEqual(choice["meal_shape"], expected_shape)
            self.assertEqual(choice["production_strategy"], expected_production)
            self.assertEqual(choice["heat_source"], "stovetop")
            self.assertIn(structure, choice["candidate_id"])

    def test_builder_rejects_a_selected_household_exclusion(self):
        kitchen = kitchen_payload()
        kitchen["meal_preferences"] = {"excluded_items": ["Onions"]}
        request = {
            "mode": "build_your_meal",
            "kitchen": kitchen,
            "selections": {
                "protein": "Chicken breast",
                "produce": ["Onions"],
                "cooking_method": "skillet",
                "serving_temperature": "hot",
            },
        }

        with self.assertRaisesRegex(APIContractError, "listed in My Kitchen exclusions"):
            get_recipe_list(request)

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
            "production_strategy", "production_label", "heat_source",
            "equipment_strategy",
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
        self.assertTrue(any(line.startswith("Chicken breast — Frozen Raw") for line in recipe["ingredients"]))
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
        self.assertTrue(any(item["meal_structure"] == "composed_plate" for item in candidates))
        self.assertTrue(any(item["meal_structure"] == "layered_bowl" for item in candidates))
        self.assertTrue(all(item["production_strategy"] for item in candidates))
        self.assertTrue(all(item["equipment_strategy"] == "adaptive" for item in candidates))

    def test_reordered_ingredients_do_not_create_duplicate_meal_ideas(self):
        kitchen = diverse_kitchen_payload()
        kitchen["inventory"].extend([
            {"name": "Tomatoes", "form": "Fresh Raw", "amount": "plenty"},
            {"name": "Garlic", "form": "Fresh Raw", "amount": "plenty"},
            {"name": "Ground beef", "form": "Fresh Raw", "amount": "plenty"},
        ])

        candidates = get_recipe_list(kitchen)["candidates"]
        # Candidate ids can differ, but a reordered component bundle may not
        # occupy another card in the same family and structure.
        signatures = [(
                item["protein"].lower(),
                tuple(sorted(part.strip().lower() for part in item["vegetable"].split(" & ") if part.strip())),
                (item.get("foundation") or "").lower(),
                item["dish_family"],
                item["meal_structure"],
            ) for item in candidates]
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_make_a_meal_assortment_uses_effort_and_real_variety(self):
        low_kitchen = diverse_kitchen_payload()
        low_kitchen["effort"] = "Low"
        low = get_recipe_list(low_kitchen)["candidates"]

        high_kitchen = diverse_kitchen_payload()
        high_kitchen["effort"] = "High"
        high = get_recipe_list(high_kitchen)["candidates"]

        self.assertEqual(low[0]["selection_badge"], "Best fit")
        self.assertTrue(any(item["selection_badge"] == "Lowest effort" for item in low))
        self.assertTrue(all(item["effort"] <= 9 for item in low))
        self.assertTrue(any(item["effort"] > 8 for item in high))
        self.assertGreaterEqual(len({item["protein"] for item in low}), 3)
        self.assertGreaterEqual(len({item["dish_family"] for item in low}), 3)
        self.assertTrue(all(item["effort_label"] for item in low))
        self.assertTrue(all(item["selection_reasons"] for item in low))

    def test_recent_meal_history_rotates_the_leading_choice(self):
        kitchen = diverse_kitchen_payload()
        original = get_recipe_list(kitchen)["candidates"][0]
        kitchen["meal_preferences"] = {"recent_meals": [{
            "title": original["title"],
            "protein": original["protein"],
            "dish_family": original["dish_family"],
        }]}

        rotated = get_recipe_list(kitchen)["candidates"][0]

        self.assertNotEqual(rotated["candidate_id"], original["candidate_id"])

    def test_expiring_inventory_can_be_selected_as_use_soon(self):
        kitchen = diverse_kitchen_payload()
        kitchen["inventory"][0]["expiration_date"] = date.today().isoformat()

        candidates = get_recipe_list(kitchen)["candidates"]
        canned_chicken = next(item for item in candidates if item["protein"] == "Canned chicken")

        self.assertTrue(any("uses soon: Canned chicken" in reason for reason in canned_chicken["selection_reasons"]))
        self.assertTrue(any(item["selection_badge"] == "Use soon" for item in candidates))

    def test_opened_recipe_lists_only_its_selected_components(self):
        kitchen = diverse_kitchen_payload()
        candidate = next(
            item for item in get_recipe_list(kitchen)["candidates"]
            if item["protein"] == "Canned chicken"
        )

        recipe = get_recipe({"candidate_id": candidate["candidate_id"], "kitchen": kitchen})

        self.assertFalse(any(item.startswith("White beans") for item in recipe["ingredients"]))
        self.assertFalse(any(item.startswith("Cheese") for item in recipe["ingredients"]))
        self.assertFalse(any(item.startswith("Eggs") for item in recipe["ingredients"]))

        soup = next(item for item in get_recipe_list(kitchen)["candidates"] if item["meal_shape"] == "soup")
        soup_recipe = get_recipe({"candidate_id": soup["candidate_id"], "kitchen": kitchen})
        self.assertTrue(any(item.startswith("Chicken broth") for item in soup_recipe["ingredients"]))

    def test_cooked_bean_soup_is_rustic_broth_soup_not_a_cream_pan_sauce(self):
        kitchen = cooked_bean_soup_payload()
        candidate = get_recipe_list(kitchen)["candidates"][0]
        recipe = get_recipe({"candidate_id": candidate["candidate_id"], "kitchen": kitchen})

        ingredients = "\n".join(recipe["ingredients"])
        plan = "\n".join(item["text"] for item in recipe["plan_items"])
        first_action = recipe["steps"][0]

        self.assertEqual(candidate["meal_shape"], "soup")
        self.assertTrue(first_action.startswith("Minutes 0–2:"))
        self.assertIn("Prep Carrots", first_action)
        self.assertNotIn("Prep White beans", plan)
        self.assertIn("medium heat", plan)
        self.assertIn("3 cups of Chicken broth", plan)
        self.assertNotIn("scrape up", plan)
        self.assertIn("Garlic powder", plan)
        self.assertIn("Onion powder", plan)
        self.assertIn("Black pepper", plan)
        self.assertIn("mash about one-third", plan)
        self.assertNotIn("protein is safe", plan)
        self.assertNotIn("Milk", ingredients)
        self.assertNotIn("Cornstarch", ingredients)
        self.assertNotIn("Cold water", ingredients)
        self.assertNotIn("Cooking oil or butter", ingredients)

    def test_cooked_bean_soup_can_use_blender_when_energy_and_equipment_allow(self):
        kitchen = cooked_bean_soup_payload("Medium", ["Stovetop", "Immersion blender"])
        candidate = get_recipe_list(kitchen)["candidates"][0]
        recipe = get_recipe({"candidate_id": candidate["candidate_id"], "kitchen": kitchen})
        plan = "\n".join(item["text"] for item in recipe["plan_items"])

        self.assertIn("For a smooth soup, blend until creamy", plan)
        self.assertNotIn("mash about one-third", plan)

    def test_opened_recipe_includes_forms_and_complete_seasoning(self):
        kitchen = diverse_kitchen_payload()
        kitchen["equipment"] = [{"name": "Microwave"}]
        kitchen["effort"] = "High"
        candidate = next(
            item for item in get_recipe_list(kitchen)["candidates"]
            if item["candidate_id"].startswith("skillet-chicken-breast")
        )

        recipe = get_recipe({"candidate_id": candidate["candidate_id"], "kitchen": kitchen})

        self.assertTrue(any(line.startswith("Chicken breast — Frozen Raw") for line in recipe["ingredients"]))
        self.assertTrue(any(line.startswith("Onions — Fresh Raw · about ") for line in recipe["ingredients"]))
        self.assertTrue(any(line.startswith("Carrots — Fresh Raw · about ") for line in recipe["ingredients"]))
        self.assertNotIn("Garlic powder — 1/2 teaspoon", recipe["ingredients"])
        self.assertNotIn("Black pepper — 1/4 teaspoon", recipe["ingredients"])
        adjustments = {item["name"]: item for item in recipe["ingredient_adjustments"]}
        self.assertEqual(adjustments["Garlic powder"]["status"], "Omit")
        self.assertEqual(adjustments["Black pepper"]["status"], "Omit")
        self.assertEqual(
            len(recipe["ingredients"]),
            len({item.split(" — ", 1)[0].lower() for item in recipe["ingredients"]}),
        )
        later_steps = " ".join(recipe["steps"][4:]).lower()
        self.assertNotIn("frozen chicken", later_steps)
        self.assertNotIn("the foundation", " ".join(recipe["steps"]).lower())
        self.assertFalse(any("main cooking is done" in step.lower() for step in recipe["steps"]))

    def test_numbered_plan_contains_actions_and_handles_frozen_ground_beef(self):
        kitchen = frozen_ground_beef_payload()
        kitchen["effort"] = "High"
        candidate = next(
            item for item in get_recipe_list(kitchen)["candidates"]
            if item.get("foundation") == "White rice"
        )

        recipe = get_recipe({"candidate_id": candidate["candidate_id"], "kitchen": kitchen})
        plan = " ".join(recipe["steps"])
        all_statements = " ".join(item["text"] for item in recipe["plan_items"])

        self.assertTrue(any(line.startswith("Ground beef — Frozen Raw") for line in recipe["ingredients"]))
        self.assertTrue(recipe["steps"][0].startswith("Minutes 0–2:"))
        self.assertIn("Measure the rice", recipe["steps"][0])
        self.assertNotIn("Tonight we are making", plan)
        self.assertNotIn("Plan on about", plan)
        self.assertNotIn("Gather the ingredients", plan)
        self.assertIn("Tonight we are making", all_statements)
        self.assertNotIn("Plan on about", all_statements)
        self.assertIn("gather the ingredients", all_statements)
        self.assertIn("microwave defrost setting", plan)
        self.assertIn("microwave defrost setting", plan)
        self.assertIn("no pink ground meat remains", plan)
        self.assertIn("30 seconds after the last pink disappears", plan)
        self.assertNotIn("food thermometer", plan)
        self.assertIn("same skillet", plan)
        self.assertNotIn("Slice Ground beef", plan)
        self.assertIn("Prepare these first", plan)
        self.assertNotIn("While Ground beef thaws", plan)
        self.assertNotIn("ingredient prep is handled", plan.lower())
        self.assertFalse(any("Prep is complete" in step for step in recipe["steps"]))
        self.assertFalse(any("Now the cooking begins" in step for step in recipe["steps"]))
        self.assertLess(plan.index("microwave defrost setting"), plan.index("Heat the skillet"))

        kinds = [item["kind"] for item in recipe["plan_items"]]
        self.assertEqual(kinds[:3], ["info", "info", "action"])
        self.assertFalse(any(
            "come to pressure" in item["text"]
            or "natural release" in item["text"]
            or "Cook the rice at high pressure" in item["text"]
            for item in recipe["plan_items"]
        ))
        self.assertFalse(any(
            "come to pressure" in step for step in recipe["steps"]
        ))
        thaw_step = next(step for step in recipe["steps"] if "microwave defrost setting" in step)
        prep_step = next(step for step in recipe["steps"] if "Ingredient Prep:" in step)
        self.assertTrue(thaw_step.startswith("Minutes 16–23:"))
        self.assertTrue(prep_step.startswith("Minutes 4–16:"))
        self.assertIn("\n\n", prep_step)
        self.assertEqual(recipe["missing_items"], [])
        adjustments = {item["name"]: item for item in recipe["ingredient_adjustments"]}
        self.assertEqual(
            adjustments["Cooking oil or butter"]["resolved_name"],
            "Rendered fat from Ground beef",
        )
        self.assertEqual(adjustments["Onion powder"]["status"], "Omit")
        self.assertIn("provides this flavor identity", adjustments["Onion powder"]["omission_consequence"])
        self.assertEqual(adjustments["Cornstarch"]["status"], "Omit")
        self.assertNotIn("Chicken broth", recipe["missing_items"])
        self.assertNotIn("Milk", recipe["missing_items"])
        self.assertNotIn("Cold water", recipe["missing_items"])
        self.assertNotIn("Salt", recipe["missing_items"])
        self.assertIn("Divide White rice among plates", recipe["steps"][-1])
        self.assertEqual(recipe["plan_items"][-1], {
            "kind": "info", "text": "Nicely done. Dinner is ready.",
        })
        self.assertLess(plan.index("Taste the sauce"), plan.index("Divide White rice among plates"))

    def test_ground_beef_carrot_skillet_is_one_pan_and_uses_honest_timing(self):
        candidate = generate_candidates(
            "Ground beef", "Onions & Carrots", "", "Comfort Food",
            "Low", "Budget", 60, 4, 1,
            vegetable_names=["Onions", "Carrots"],
            protein_state="Fresh Raw",
            available_items=[
                "Ground beef", "Onions", "Carrots", "Chicken broth", "Milk",
                "Garlic powder", "Onion powder", "Black pepper",
            ],
        )[0]
        recipe = build_recipe_from_candidate(candidate)
        plan = "\n".join(recipe["action_steps"])

        self.assertGreaterEqual(candidate["minutes"], 22)
        self.assertLessEqual(candidate["minutes"], 24)
        self.assertIn("1/4-inch dice", plan)
        self.assertIn("1/2-inch dice", plan)
        self.assertIn("Cook for about 4 minutes", plan)
        self.assertIn("bloom in the hot fat for about 30 seconds", plan)
        self.assertIn("8–10 minutes", plan)
        self.assertIn("Carrots reaches this outcome: Tender pieces", plan)
        self.assertIn("Onions reaches this outcome: Soft, sweet, aromatic pieces", plan)
        self.assertIn("Spoon everything in the skillet", plan)
        self.assertNotIn("Add Ground beef to the plates", plan)
        self.assertNotIn("Good job—the main cooking is done", plan)

    def test_excluded_component_is_rejected_before_ranking(self):
        candidates = generate_candidates(
            "Ground beef", "Onions", "", "Comfort Food",
            "Low", "Budget", 60, 4, 10,
            vegetable_names=["Onions"],
            available_items=["Ground beef", "Onions", "Chicken broth", "Milk"],
            excluded_items=["Ground beef"],
        )

        self.assertEqual(candidates, [])

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

    def test_ribeye_uses_visible_flip_cue_thermometer_rest_and_separate_mash(self):
        request = {
            "mode": "build_your_meal", "kitchen": {"inventory": []},
            "selections": {
                "protein": "Ribeye steak", "protein_state": "Fresh Raw",
                "produce": ["Broccoli"], "produce_forms": {"Broccoli": "Fresh"},
                "foundation": "Mashed potatoes", "cuisine": "Comfort Food",
                "cooking_method": "skillet", "meal_structure": "composed_plate",
                "serving_temperature": "hot", "servings": 2,
                "eater_profiles": {"standard": 2},
            },
        }
        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})
        plan = " ".join(item["text"] for item in recipe["plan_items"])

        self.assertIn("halfway to two-thirds up the side", plan)
        self.assertIn("145°F", plan)
        self.assertIn("followed by at least a 3-minute rest", plan)
        self.assertIn("Keep it separate from the protein cooking vessel", plan)
        self.assertIn("retained color", plan)
        self.assertNotIn("cook until ready", plan.lower())

    def test_opened_partial_can_gets_age_and_safety_check_before_prep(self):
        kitchen = {
            "inventory": [
                {"name": "Rotisserie chicken", "form": "Ready to Eat", "quantity": 1, "unit": "piece"},
                {"name": "Navy beans", "form": "Canned", "quantity": 0.5, "unit": "can",
                 "opened_at": date.today().isoformat(), "refrigerated_after_opening": True},
            ]
        }
        request = {
            "mode": "build_your_meal", "kitchen": kitchen,
            "selections": {"protein": "Rotisserie chicken", "foundation": "Navy beans",
                           "produce": [], "cooking_method": "skillet", "meal_structure": "integrated",
                           "serving_temperature": "hot", "servings": 2},
        }
        choice = get_recipe_list(request)["candidates"][0]
        recipe = get_recipe({"candidate_id": choice["candidate_id"], "kitchen": request})
        actions = [item["text"] for item in recipe["plan_items"] if item["kind"] == "action"]

        check_index = next(i for i, text in enumerate(actions) if "opened Navy beans" in text)
        prep_index = next(i for i, text in enumerate(actions) if "Drain and rinse Navy beans" in text)
        self.assertLess(check_index, prep_index)
        safety_text = " ".join(actions).lower()
        self.assertIn("confirm it stayed refrigerated", safety_text)
        self.assertIn("storage-time limit", safety_text)

    def test_appetite_can_and_aromatic_roles_are_quantity_aware(self):
        candidate = generate_candidates(
            "Canned chicken", "Onions", "Navy beans", "Comfort Food",
            "Low", "Budget", 60, 3, 1, vegetable_names=["Onions"],
            protein_state="Canned", available_items=["Canned chicken", "Onions", "Navy beans", "Onion powder"],
            component_forms={"Canned chicken": "Canned", "Onions": "Fresh", "Navy beans": "Canned"},
            inventory_lots=[{"name": "Navy beans", "form": "Canned", "quantity": 3, "unit": "can"}],
            eater_profiles={"light": 1, "standard": 1, "big": 1}, use_all_cans=True,
        )[0]
        statuses = {item["name"]: item["status"] for item in candidate["inventory_requirements"]}

        self.assertEqual(candidate["effective_portions"], 3.25)
        self.assertEqual(candidate["quantity_plan"]["navy beans"]["display"], "3 cans")
        self.assertIn("entire meal larger", candidate["quantity_note"])
        self.assertEqual(statuses["Onion powder"], "Omit")

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
