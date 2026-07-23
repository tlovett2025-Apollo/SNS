import csv
from io import TextIOWrapper
import unittest
from zipfile import ZipFile

from config import DB_PATH
from inventory_contract import (
    InventoryContractError,
    inventory_profile,
    normalize_inventory_lot,
    normalize_unit,
    quantity_in_basis,
)
from ko_contract import SAFETY_GATES, audit_behavior
from recipe_engine import _quantity_plan
from sample_pantry_catalog import SAMPLE_PANTRY_ZIP


def regional_pantry_rows():
    rows = {}
    with ZipFile(SAMPLE_PANTRY_ZIP) as archive:
        for filename in sorted(
            name for name in archive.namelist()
            if name.startswith("csv/") and name.endswith(".csv")
        ):
            with archive.open(filename) as raw:
                for row in csv.DictReader(TextIOWrapper(raw, encoding="utf-8-sig")):
                    key = (row["name"].strip(), row["form"].strip())
                    rows[key] = row
    return tuple(rows.values())


class InventoryContractTests(unittest.TestCase):
    def test_every_regional_pantry_form_and_unit_has_a_complete_contract(self):
        rows = regional_pantry_rows()
        self.assertEqual(len(rows), 140)
        failures = []
        for row in rows:
            try:
                profile = inventory_profile(row["name"], row["form"], db_path=DB_PATH)
                if normalize_unit(row["unit"]) not in profile.allowed_units:
                    failures.append((row["name"], row["form"], row["unit"], "unit"))
                    continue
                report = audit_behavior(
                    profile.name, profile.role, profile.default_form, db_path=DB_PATH
                )
                failed_gates = [name for name in SAFETY_GATES if not report.checks[name]]
                if failed_gates:
                    failures.append((row["name"], row["form"], row["unit"], failed_gates))
            except InventoryContractError as exc:
                failures.append((row["name"], row["form"], row["unit"], str(exc)))
        self.assertEqual(failures, [])

    def test_one_pound_of_chicken_is_four_standard_piece_portions(self):
        self.assertEqual(quantity_in_basis(1, "lb", "pieces"), 4)
        self.assertEqual(quantity_in_basis(8, "oz", "pieces"), 2)

        _effective, plan, note = _quantity_plan(
            ["Chicken breast"],
            {"Chicken breast": "Fresh Raw"},
            [{"name": "Chicken breast", "form": "Fresh Raw", "quantity": 1, "unit": "lb"}],
            4,
            {},
            False,
            {"Chicken breast": "protein"},
        )
        self.assertEqual(plan["chicken breast"]["available"], 4)
        self.assertEqual(plan["chicken breast"]["shortfall"], 0)
        self.assertNotIn("Only about 1", note)

    def test_unknown_package_weight_is_not_invented(self):
        self.assertIsNone(quantity_in_basis(1, "package", "pieces"))
        self.assertEqual(
            quantity_in_basis(2, "package", "pieces", package_weight_oz=8), 4
        )

    def test_legacy_item_unit_migrates_to_the_ko_default(self):
        lot, profile = normalize_inventory_lot(
            {"name": "Chicken broth", "form": "Shelf-stable", "quantity": 1, "unit": "item"},
            "Chicken broth",
            db_path=DB_PATH,
            strict=True,
        )
        self.assertEqual(lot["unit"], profile.default_unit)

    def test_an_incompatible_unit_is_rejected_at_the_persistence_boundary(self):
        with self.assertRaisesRegex(InventoryContractError, "cannot be stored"):
            normalize_inventory_lot(
                {"name": "Chicken breast", "form": "Fresh Raw", "quantity": 1, "unit": "jar"},
                "Chicken breast",
                db_path=DB_PATH,
                strict=True,
            )

    def test_thin_sliced_chicken_preserves_its_precise_inventory_form(self):
        lot, profile = normalize_inventory_lot(
            {
                "name": "Chicken breast",
                "form": "Thin-sliced Raw",
                "quantity": 4,
                "unit": "pieces",
                "storage_location": "Fridge",
            },
            "Chicken breast",
            db_path=DB_PATH,
            strict=True,
        )
        self.assertEqual(lot["form"], "Thin-sliced Raw")
        self.assertEqual(profile.default_form, "Thin-sliced Raw")

    def test_ground_beef_defaults_to_weight_not_ambiguous_packages(self):
        profile = inventory_profile("Ground beef", "Fresh Raw", db_path=DB_PATH)

        self.assertEqual(profile.default_unit, "lb")
        self.assertEqual(profile.allowed_units, ("lb", "oz", "package"))

    def test_pineapple_has_distinct_canned_and_dried_pantry_contracts(self):
        canned = inventory_profile("Pineapple", "Canned", db_path=DB_PATH)
        dried = inventory_profile("Pineapple", "Dried", db_path=DB_PATH)

        self.assertEqual(canned.default_storage, "Pantry")
        self.assertEqual(canned.default_unit, "can")
        self.assertEqual(dried.default_storage, "Pantry")
        self.assertEqual(dried.default_unit, "bag")


if __name__ == "__main__":
    unittest.main()
