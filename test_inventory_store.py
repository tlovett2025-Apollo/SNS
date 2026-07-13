import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from household_inventory import ensure_inventory_schema
from inventory_store import (
    inventory_payload, load_saved_form_ids, local_context, save_inventory,
)


class InventoryStoreAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "adapter.db"
        with closing(sqlite3.connect(self.db_path)) as con:
            with con:
                con.executescript("""
                    CREATE TABLE users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, display_name TEXT NOT NULL, default_servings INTEGER, leftovers_ok INTEGER);
                    CREATE TABLE ingredients (ingredient_id INTEGER PRIMARY KEY, name TEXT, category TEXT);
                    CREATE TABLE ingredient_forms (form_id INTEGER PRIMARY KEY, ingredient_id INTEGER, form_name TEXT);
                    CREATE TABLE user_inventory (inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,ingredient_id INTEGER,form_id INTEGER,prep_id INTEGER,quantity REAL,unit TEXT,storage_location TEXT,expiration_date TEXT,confidence_level TEXT);
                """)
                con.execute("INSERT INTO ingredients VALUES (1,'Rice','Foundations')")
                con.execute("INSERT INTO ingredient_forms VALUES (10,1,'Dry')")
                ensure_inventory_schema(con)
        self.context = local_context(self.db_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_adapter_saves_and_loads_forms(self):
        saved, pending = save_inventory(
            [{"ingredient_id": 1, "form_id": 10, "name": "Rice", "form_name": "Dry", "storage": "Pantry"}],
            [], self.db_path, self.context,
        )
        self.assertEqual((saved, pending), (1, 0))
        self.assertEqual(load_saved_form_ids(self.db_path, self.context), {10})

    def test_payload_exposes_household_recipe_contract(self):
        payload = inventory_payload(self.context, [], [])
        self.assertEqual(payload["recipe_request"], {"household_id": self.context["household_id"]})


if __name__ == "__main__":
    unittest.main()
