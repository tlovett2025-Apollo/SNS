"""Round 5 matrix for retail identity, directions, and promotion safety."""

import unittest

from retail_products import (
    PREPARATION_CONTRACTS,
    PRODUCT_KINDS,
    classify_product,
    preparation_contract,
    retail_product_draft,
)


class RetailProductTests(unittest.TestCase):

    def test_every_product_kind_has_a_preparation_policy(self):
        self.assertEqual(set(PRODUCT_KINDS), set(PREPARATION_CONTRACTS))
        for kind in PRODUCT_KINDS:
            with self.subTest(kind=kind):
                contract = preparation_contract(kind)
                self.assertTrue(contract.meal_job)
                self.assertTrue(contract.direction_policy)

    def test_common_convenience_products_classify_by_retail_behavior(self):
        cases = {
            "Ginger Ale; soft drinks": "prepared_beverage",
            "Boxed scalloped potatoes; potato side dishes": "boxed_side",
            "Hawaiian rolls; breads": "bread_product",
            "Green beans; canned vegetables; can": "canned_ingredient",
            "Tomato salsa; condiments": "sauce_or_condiment",
        }
        for evidence, expected in cases.items():
            with self.subTest(evidence=evidence):
                self.assertEqual(
                    expected,
                    classify_product({"product_name": evidence}),
                )

    def test_provider_directions_are_evidence_not_executable_knowledge(self):
        draft = retail_product_draft({
            "product_name": "Boxed scalloped potatoes",
            "categories": "Boxed sides",
            "preparation": "Add milk and butter; bake 25 minutes.",
        }, "012345678901")

        self.assertEqual("boxed_side", draft.product_kind)
        self.assertTrue(draft.household_confirmation_required)
        self.assertFalse(draft.executable_directions)
        self.assertEqual("review_required", draft.enrichment_status)
        self.assertEqual("retail_product_registry", draft.promotion_target)
        self.assertIn("Add milk", draft.preparation_directions)

    def test_beverage_contract_cannot_become_an_ingredient_recipe(self):
        contract = preparation_contract("prepared_beverage")
        self.assertEqual("beverage", contract.meal_job)
        self.assertFalse(contract.executable_after_confirmation)


if __name__ == "__main__":
    unittest.main()

