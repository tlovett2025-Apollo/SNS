"""Round 6 matrix for household safety and preference strength."""

import unittest

from household_fit import assess_candidate_fit, compile_household_fit


class HouseholdFitTests(unittest.TestCase):

    def test_safety_fields_expand_before_recipe_generation(self):
        profile = compile_household_fit({
            "allergies": "Peanuts, shellfish",
            "never_include": "Pork, grapefruit",
            "usually_avoid": "milk",
            "favorite_directions": "Tex-Mex, Italian",
        })

        exclusions = {item.lower() for item in profile.hard_exclusions}
        self.assertIn("shrimp", exclusions)
        self.assertIn("peanut butter", exclusions)
        self.assertIn("bacon", exclusions)
        self.assertIn("grapefruit", exclusions)
        self.assertNotIn("milk", exclusions)
        self.assertEqual(("milk",), profile.usually_avoid)

    def test_person_specific_safety_uses_only_people_eating_this_meal(self):
        preferences = {"people": [
            {"name": "A", "allergies": ["shellfish"]},
            {"name": "B", "allergies": ["peanuts"]},
        ]}
        profile = compile_household_fit(preferences, ["A"])
        exclusions = {item.lower() for item in profile.hard_exclusions}

        self.assertEqual(("A",), profile.people_in_scope)
        self.assertIn("shrimp", exclusions)
        self.assertNotIn("peanut butter", exclusions)

    def test_allergy_is_a_gate_while_avoid_and_favorite_are_rank_weights(self):
        profile = compile_household_fit({
            "allergies": ["shellfish"],
            "usually_avoid": ["Milk"],
            "favorite_directions": ["Italian"],
        })
        safe_fit = assess_candidate_fit({
            "protein": "Chicken breast", "cuisine": "Italian",
            "inventory_requirements": [{"name": "Milk", "status": "Have"}],
        }, profile)
        blocked_fit = assess_candidate_fit({
            "protein": "Shrimp", "cuisine": "Italian",
            "inventory_requirements": [],
        }, profile)

        self.assertTrue(safe_fit["safe"])
        self.assertEqual(-13, safe_fit["preference_adjustment"])
        self.assertFalse(blocked_fit["safe"])
        self.assertIn("shrimp", {item.lower() for item in blocked_fit["blocked"]})

    def test_dietary_constraints_compile_to_hard_exclusions(self):
        vegan = compile_household_fit({"dietary_constraints": ["vegan"]})
        exclusions = {item.lower() for item in vegan.hard_exclusions}
        self.assertIn("chicken", exclusions)
        self.assertIn("eggs", exclusions)
        self.assertIn("milk", exclusions)


if __name__ == "__main__":
    unittest.main()
