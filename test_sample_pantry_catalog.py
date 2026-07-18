import unittest

from config import DB_PATH
from ko_behavior import resolve_behavior
from sample_pantry_catalog import (
    audit_sample_pantries,
    audit_summary,
    sample_pantry_forms,
    sample_pantry_names,
)


class SamplePantryCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = audit_sample_pantries()
        cls.summary = audit_summary(cls.rows)
        cls.forms = sample_pantry_forms()

    def test_every_regional_sample_item_is_canonical_and_operational(self):
        self.assertEqual(len(sample_pantry_names()), 139)
        self.assertEqual(self.summary["resolved_items"], 139)
        self.assertEqual(self.summary["operational_items"], 139)
        self.assertEqual(self.summary["missing_catalog"], [])
        self.assertEqual(self.summary["missing_behavior"], [])
        self.assertEqual(self.summary["food_role_without_public_method"], [])

    def test_real_world_forms_do_not_erase_cooking_routes(self):
        self.assertEqual(self.forms["Cornbread"], ("Shelf-stable",))
        self.assertEqual(self.forms["Corned beef"], ("Fresh Raw",))
        self.assertIn("Canned", self.forms["Corn"])
        self.assertIn("Canned", self.forms["Green beans"])
        self.assertIn("Canned", self.forms["Collard greens"])
        self.assertIn("Canned", self.forms["Mustard greens"])

    def test_canned_corn_and_greens_have_real_casserole_knowledge(self):
        for name in ("Corn", "Collard greens", "Mustard greens"):
            with self.subTest(name=name):
                behavior = resolve_behavior(name, "vegetable", "Canned", "casserole", DB_PATH)
                self.assertIsNotNone(behavior.method)
                self.assertEqual(behavior.method.method, "casserole")
                self.assertIn("canned", behavior.method.forms)


if __name__ == "__main__":
    unittest.main()
