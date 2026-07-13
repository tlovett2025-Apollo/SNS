import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from inventory_store import PROTOTYPE_USER, inventory_payload, load_saved_form_ids, save_inventory


SCHEMA = """
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    default_servings INTEGER DEFAULT 4,
    leftovers_ok INTEGER DEFAULT 1
);
CREATE TABLE user_inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    ingredient_id INTEGER NOT NULL,
    form_id INTEGER,
    storage_location TEXT,
    confidence_level TEXT
);
"""


class InventoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "inventory.db"
        with closing(sqlite3.connect(self.db_path)) as con:
            with con:
                con.executescript(SCHEMA)
                con.execute(
                    "INSERT INTO users (display_name) VALUES ('Real Household')"
                )
                con.execute(
                    "INSERT INTO user_inventory (user_id,ingredient_id,form_id) VALUES (1,99,999)"
                )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_save_and_reload_isolated_prototype_inventory(self):
        rows = [
            {"ingredient_id": 1, "form_id": 10, "name": "Rice", "form_name": "Dry", "storage": "Pantry"},
            {"ingredient_id": 2, "form_id": 20, "name": "Corn", "form_name": "Frozen", "storage": "Freezer"},
        ]
        self.assertEqual(save_inventory(rows, self.db_path), 2)
        self.assertEqual(load_saved_form_ids(self.db_path), {10, 20})
        with closing(sqlite3.connect(self.db_path)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM user_inventory WHERE user_id=1").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM users WHERE display_name=?", (PROTOTYPE_USER,)).fetchone()[0], 1)

    def test_second_save_replaces_only_prototype_rows(self):
        first = [{"ingredient_id": 1, "form_id": 10, "storage": "Pantry"}]
        second = [{"ingredient_id": 2, "form_id": 20, "storage": "Freezer"}]
        save_inventory(first, self.db_path)
        save_inventory(second, self.db_path)
        self.assertEqual(load_saved_form_ids(self.db_path), {20})

    def test_payload_marks_unrecognized_quick_entries(self):
        known = [{"ingredient_id": 1, "form_id": 10, "name": "Rice", "form_name": "Dry", "storage": "Pantry"}]
        custom = [{"name": "Mystery crackers", "form_name": "On hand", "section": "Pantry"}]
        payload = inventory_payload(known, custom)
        self.assertTrue(payload[0]["ckb_known"])
        self.assertFalse(payload[1]["ckb_known"])
        self.assertIsNone(payload[1]["ingredient_id"])


if __name__ == "__main__":
    unittest.main()
