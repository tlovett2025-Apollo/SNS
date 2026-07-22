import unittest

from recipe_validation import validate_recipe


class RecipeValidationTests(unittest.TestCase):
    def test_dry_pasta_cannot_be_assembled_uncooked_in_a_casserole(self):
        candidate = {
            "cooking_method": "casserole",
            "foundation": "Egg noodles",
            "component_forms": {"Egg noodles": "Dry"},
            "proteins": [],
            "vegetable": "",
            "selected_extras": [],
            "inventory_requirements": [],
        }
        plan = [{
            "kind": "action",
            "text": "Arrange Egg noodles in the baking dish and bake until hot.",
        }]

        result = validate_recipe(candidate, plan)

        self.assertFalse(result["production_ready"])
        self.assertIn(
            "Dry Egg noodles must be boiled and drained before casserole assembly.",
            result["errors"],
        )

    def test_substitution_and_omission_resolutions_are_authoritative(self):
        candidate = {
            "cooking_method": "skillet",
            "proteins": [], "vegetable": "", "foundation": "",
            "selected_extras": [],
            "inventory_requirements": [
                {"name": "Olive oil", "status": "Substitute", "resolved_name": "Butter", "quantity": "1 tablespoon"},
                {"name": "Cornstarch", "status": "Omit", "resolved_name": None, "quantity": "1 tablespoon"},
            ],
        }
        plan = [{
            "kind": "action",
            "text": "Measure Butter. Heat Olive oil, then whisk in Cornstarch.",
        }]

        result = validate_recipe(candidate, plan)

        self.assertFalse(result["production_ready"])
        self.assertIn("Instructions use Olive oil after the kitchen check substituted Butter.", result["errors"])
        self.assertIn("Instructions use omitted ingredient Cornstarch.", result["errors"])

    def test_frozen_raw_component_requires_readiness_outside_the_timed_plan(self):
        candidate = {
            "cooking_method": "skillet",
            "proteins": [{"name": "Chicken breast", "state": "Frozen Raw", "role": "main"}],
            "vegetable": "", "foundation": "", "selected_extras": [],
            "inventory_requirements": [],
        }
        plan = [{"kind": "action", "text": "Brown Chicken breast until it reaches 165°F."}]

        result = validate_recipe(candidate, plan)

        self.assertFalse(result["production_ready"])
        self.assertIn("Frozen Chicken breast has no pre-cook thaw-readiness statement.", result["errors"])

        plan.insert(0, {
            "kind": "info",
            "text": "Before Step 1, fully thaw Chicken breast. The timed cooking plan assumes it is ready to cook.",
        })
        self.assertTrue(validate_recipe(candidate, plan)["production_ready"])

        plan.append({"kind": "action", "text": "Defrost Chicken breast in the microwave."})
        self.assertIn(
            "Frozen Chicken breast thawing appeared inside the timed cooking plan.",
            validate_recipe(candidate, plan)["errors"],
        )


if __name__ == "__main__":
    unittest.main()
