import sqlite3
import unittest

from api_service import get_meal_builder_options, get_recipe, get_recipe_list
from config import DB_PATH
from equipment_profiles import choose_braise_equipment
from ko_behavior import resolve_behavior
from recipe_engine import _quantity_plan, _sauce_for_cuisine
from sauce_profiles import get_sauce_profile


class CapabilityMatrixTests(unittest.TestCase):
    def setUp(self):
        self.options = get_meal_builder_options({"equipment": [{"name": "Grill"}]})

    def test_every_public_catalog_item_has_a_verified_behavior_family(self):
        for group, role, default_form in (
            ("proteins", "protein", "Fresh Raw"),
            ("produce", "vegetable", "Fresh"),
            ("foundations", "foundation", ""),
        ):
            for item in self.options[group]:
                behavior = resolve_behavior(
                    item["name"], role, item.get("form") or default_form, db_path=DB_PATH
                )
                self.assertIsNotNone(behavior.primary_family, f"{group}: {item['name']}")

    def test_common_method_coverage_cannot_silently_regress(self):
        proteins = self.options["proteins"]
        produce = self.options["produce"]

        def covered(items, role, form, environment):
            return sum(
                resolve_behavior(
                    item["name"], role, item.get("form") or form,
                    environment, DB_PATH,
                ).method is not None
                for item in items
            )

        self.assertGreaterEqual(covered(proteins, "protein", "Fresh Raw", "soup"), 26)
        self.assertGreaterEqual(covered(proteins, "protein", "Fresh Raw", "casserole"), 20)
        self.assertGreaterEqual(covered(proteins, "protein", "Fresh Raw", "handheld"), 23)
        self.assertGreaterEqual(covered(produce, "vegetable", "Fresh", "soup"), 83)
        self.assertGreaterEqual(covered(produce, "vegetable", "Fresh", "casserole"), 73)
        self.assertGreaterEqual(covered(produce, "vegetable", "Fresh", "handheld"), 80)

    def test_each_new_common_route_opens_as_a_production_ready_recipe(self):
        cases = (
            ("handheld", "Bread", ["Stovetop"]),
            ("casserole", "", ["Oven"]),
            ("soup", "", ["Stovetop"]),
        )
        for method, foundation, equipment in cases:
            request = {
                "mode": "build_your_meal",
                "kitchen": {
                    "inventory": [],
                    "equipment": [{"name": name} for name in equipment],
                },
                "selections": {
                    "protein": "Chicken breast", "protein_state": "Fresh Raw",
                    "produce": ["Tomatoes"], "foundation": foundation,
                    "extras": [], "cuisine": "Comfort Food",
                    "cooking_method": method, "meal_structure": "integrated",
                    "serving_temperature": "hot", "energy": "Low",
                    "time_minutes": 240, "servings": 4,
                },
            }
            candidate = get_recipe_list(request)["candidates"][0]
            recipe = get_recipe({"candidate_id": candidate["candidate_id"], "kitchen": request})
            self.assertTrue(recipe["recipe_validation"]["production_ready"], method)
            self.assertTrue(recipe["ingredients"], method)
            self.assertTrue(recipe["steps"], method)

    def test_every_public_cuisine_resolves_to_measured_sauce_knowledge(self):
        for cuisine in self.options["cuisines"]:
            profile = get_sauce_profile(_sauce_for_cuisine(cuisine))
            self.assertIsNotNone(profile, cuisine)
            self.assertTrue(profile.ingredients, cuisine)
            self.assertTrue(all(item.quantity for item in profile.ingredients), cuisine)

    def test_equipment_selection_has_real_pressure_slow_and_stovetop_routes(self):
        self.assertEqual(choose_braise_equipment(["Instant Pot"], 180), "pressure cooker")
        self.assertEqual(choose_braise_equipment(["Slow cooker"], 480), "slow cooker")
        self.assertEqual(choose_braise_equipment(["Dutch oven"], 240), "dutch oven")
        self.assertEqual(choose_braise_equipment(["Stovetop"], 240), "stovetop")

        for equipment, available_minutes, expected_text in (
            ("Instant Pot", 240, "high pressure for 45 minutes"),
            ("Slow cooker", 480, "covered on LOW"),
        ):
            request = {
                "mode": "build_your_meal",
                "kitchen": {"inventory": [], "equipment": [{"name": equipment}]},
                "selections": {
                    "protein": "Beef brisket", "protein_state": "Fresh Raw",
                    "produce": ["Onions"], "foundation": "", "extras": [],
                    "cuisine": "BBQ", "cooking_method": "skillet",
                    "meal_structure": "integrated", "serving_temperature": "hot",
                    "energy": "Low", "time_minutes": available_minutes, "servings": 4,
                },
            }
            candidate = get_recipe_list(request)["candidates"][0]
            recipe = get_recipe({"candidate_id": candidate["candidate_id"], "kitchen": request})
            plan = " ".join(recipe["instructions"])
            self.assertIn(expected_text, plan)
            self.assertNotIn("for a skillet meal", plan)
            self.assertTrue(recipe["recipe_validation"]["production_ready"])

    def test_quantity_exceptions_keep_citrus_and_aromatics_practical(self):
        _, plan, _ = _quantity_plan(
            ["Limes", "Garlic", "Tomatoes"], {}, [], 7, {}, False,
            {"Limes": "vegetable", "Garlic": "vegetable", "Tomatoes": "vegetable"},
        )
        self.assertEqual(plan["limes"]["display"], "2 limes")
        self.assertEqual(plan["garlic"]["display"], "4 cloves")
        self.assertIn("cup", plan["tomatoes"]["display"])

    def test_relationship_compatibility_and_substitution_knowledge_is_populated(self):
        with sqlite3.connect(DB_PATH) as con:
            self.assertGreater(con.execute("SELECT count(*) FROM ko_relationship_rules WHERE verified=1").fetchone()[0], 0)
            self.assertGreater(con.execute("SELECT count(*) FROM compatibility_rules WHERE active=1").fetchone()[0], 0)
            self.assertGreater(con.execute("SELECT count(*) FROM substitution_rules").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
