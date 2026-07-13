import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from household_inventory import (
    InventoryAccessError,
    InventoryError,
    bootstrap_local_household,
    ensure_inventory_schema,
    get_household_inventory,
    replace_household_inventory,
    submit_pending_items,
)


BASE_SCHEMA = """
CREATE TABLE users (
 user_id INTEGER PRIMARY KEY AUTOINCREMENT, display_name TEXT NOT NULL,
 default_servings INTEGER DEFAULT 4, leftovers_ok INTEGER DEFAULT 1
);
CREATE TABLE ingredients (
 ingredient_id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL
);
CREATE TABLE ingredient_forms (
 form_id INTEGER PRIMARY KEY, ingredient_id INTEGER NOT NULL, form_name TEXT NOT NULL
);
CREATE TABLE user_inventory (
 inventory_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
 ingredient_id INTEGER NOT NULL, form_id INTEGER, prep_id INTEGER,
 quantity REAL, unit TEXT, storage_location TEXT, expiration_date TEXT,
 confidence_level TEXT
);
"""


class HouseholdInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "household.db"
        with closing(sqlite3.connect(self.db_path)) as con:
            with con:
                con.executescript(BASE_SCHEMA)
                con.executemany(
                    "INSERT INTO ingredients VALUES (?,?,?)",
                    [(1, "White rice", "Foundations"), (2, "Corn", "Vegetables")],
                )
                con.executemany(
                    "INSERT INTO ingredient_forms VALUES (?,?,?)",
                    [(10, 1, "Dry"), (20, 2, "Frozen")],
                )
        self.user_id, self.household_id = bootstrap_local_household(self.db_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def items(self):
        return [
            {"ingredient_id": 1, "form_id": 10, "storage": "Pantry", "quantity": 2, "unit": "bags"},
            {"ingredient_id": 2, "form_id": 20, "storage": "Freezer", "expiration_date": "2026-08-01"},
        ]

    def test_schema_migrates_existing_inventory_table(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            ensure_inventory_schema(con)
            columns = {row[1] for row in con.execute("PRAGMA table_info(user_inventory)")}
        self.assertIn("household_id", columns)

    def test_replace_and_reload_canonical_household_inventory(self):
        self.assertEqual(replace_household_inventory(
            self.db_path, self.household_id, self.user_id, self.items()
        ), 2)
        loaded = get_household_inventory(
            self.db_path, self.household_id, self.user_id
        )
        self.assertEqual({row["name"] for row in loaded}, {"White rice", "Corn"})
        self.assertEqual(next(row for row in loaded if row["name"] == "White rice")["quantity"], 2)

    def test_replace_is_atomic_when_a_later_item_is_invalid(self):
        replace_household_inventory(
            self.db_path, self.household_id, self.user_id, [self.items()[0]]
        )
        bad = [self.items()[1], {"ingredient_id": 999, "form_id": None}]
        with self.assertRaises(InventoryError):
            replace_household_inventory(
                self.db_path, self.household_id, self.user_id, bad
            )
        loaded = get_household_inventory(
            self.db_path, self.household_id, self.user_id
        )
        self.assertEqual([row["name"] for row in loaded], ["White rice"])

    def test_form_must_belong_to_ingredient(self):
        with self.assertRaises(InventoryError):
            replace_household_inventory(
                self.db_path, self.household_id, self.user_id,
                [{"ingredient_id": 1, "form_id": 20}],
            )

    def test_nonmember_cannot_read_or_write_household(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            with con:
                stranger = int(con.execute(
                    "INSERT INTO users (display_name) VALUES ('Stranger')"
                ).lastrowid)
        with self.assertRaises(InventoryAccessError):
            get_household_inventory(self.db_path, self.household_id, stranger)
        with self.assertRaises(InventoryAccessError):
            replace_household_inventory(self.db_path, self.household_id, stranger, [])

    def test_quick_entry_is_pending_and_does_not_edit_ckb(self):
        count = submit_pending_items(
            self.db_path, self.household_id, self.user_id,
            [{"name": "Mystery crackers", "form_name": "On hand", "section": "Pantry"}],
        )
        self.assertEqual(count, 1)
        with closing(sqlite3.connect(self.db_path)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0], 2)
            pending = con.execute(
                "SELECT raw_text,match_status FROM pending_inventory_items"
            ).fetchone()
        self.assertEqual(pending, ("Mystery crackers", "pending"))
        self.assertEqual(submit_pending_items(
            self.db_path, self.household_id, self.user_id,
            [{"name": "mystery crackers", "form_name": "On hand", "section": "Pantry"}],
        ), 0)

    def test_rejects_negative_quantity_and_bad_expiration(self):
        for item in (
            {"ingredient_id": 1, "form_id": 10, "quantity": -1},
            {"ingredient_id": 1, "form_id": 10, "expiration_date": "July someday"},
        ):
            with self.assertRaises(InventoryError):
                replace_household_inventory(
                    self.db_path, self.household_id, self.user_id, [item]
                )


if __name__ == "__main__":
    unittest.main()
