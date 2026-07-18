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

    def test_frozen_raw_component_requires_an_explicit_thaw_or_defrost_step(self):
        candidate = {
            "cooking_method": "skillet",
            "proteins": [{"name": "Chicken breast", "state": "Frozen Raw", "role": "main"}],
            "vegetable": "", "foundation": "", "selected_extras": [],
            "inventory_requirements": [],
        }
        plan = [{"kind": "action", "text": "Brown Chicken breast until it reaches 165°F."}]

        result = validate_recipe(candidate, plan)

        self.assertFalse(result["production_ready"])
        self.assertIn("Frozen Chicken breast has no explicit thawing step before cooking.", result["errors"])


if __name__ == "__main__":
    unittest.main()
