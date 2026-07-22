"""Round 3 matrix for flavor identity, coherence, and substitutions."""

import unittest

from flavor_identity import (
    FLAVOR_IDENTITIES,
    flavor_identity,
    ingredient_affinity_status,
    substitution_preserves_identity,
)
from recipe_engine import _sauce_for_cuisine, generate_candidates
from sauce_profiles import get_sauce_profile


class FlavorIdentityTests(unittest.TestCase):

    def test_every_named_identity_has_an_executable_sauce_contract(self):
        self.assertEqual(9, len(FLAVOR_IDENTITIES))
        for code, identity in FLAVOR_IDENTITIES.items():
            with self.subTest(identity=code):
                self.assertEqual(identity.sauce, _sauce_for_cuisine(identity.name))
                self.assertIsNotNone(get_sauce_profile(identity.sauce))
                self.assertTrue(identity.signature)
                self.assertTrue(identity.source)

    def test_affinity_is_a_gate_not_a_scoring_hint(self):
        self.assertEqual(
            "aligned", ingredient_affinity_status("Mexican", ["Mexican"])
        )
        self.assertEqual(
            "conflicting", ingredient_affinity_status("Italian", ["Mexican"])
        )
        self.assertEqual("neutral", ingredient_affinity_status("Italian", []))

    def test_only_trained_or_nonconflicting_substitutions_preserve_identity(self):
        self.assertTrue(
            substitution_preserves_identity(
                "Mediterranean", "Lemons", "Limes", ["Mexican"]
            )
        )
        self.assertFalse(
            substitution_preserves_identity(
                "Italian", "Lemons", "Limes", ["Mexican"]
            )
        )

    def test_conflicting_selected_extra_is_omitted_before_candidate_ranking(self):
        candidate = generate_candidates(
            "Ground beef", "Onions", "Pasta", "Italian", "Medium", "Budget",
            60, 2, 1,
            protein_state="Fresh Raw",
            available_items=[
                "Ground beef", "Onions", "Pasta", "Tomato sauce", "Garlic",
                "Olive oil", "Italian seasoning", "Salsa",
            ],
            selected_extras=["Salsa"],
            available_equipment=["Stovetop"],
            requested_method="skillet",
        )[0]
        salsa = next(
            item for item in candidate["inventory_requirements"]
            if item["name"] == "Salsa"
        )

        self.assertEqual("Omit", salsa["status"])
        self.assertFalse(salsa["required"])
        self.assertIn("Salsa", candidate["coherence_omissions"])
        self.assertEqual("italian", candidate["flavor_identity"]["code"])

    def test_aliases_resolve_to_one_identity_contract(self):
        self.assertEqual("mexican", flavor_identity("Tex-Mex").code)
        self.assertEqual("comfort_food", flavor_identity("American").code)
        self.assertEqual("mild_favorite", flavor_identity("Kid-Friendly").code)


if __name__ == "__main__":
    unittest.main()
