import sqlite3
import tempfile
import unittest
from pathlib import Path

from config import DB_PATH
from ko_behavior import (
    family_codes_for,
    resolve_behavior,
    seed_behavior_library,
)
from ko_contract import audit_behavior


class KOBehaviorFamilyTests(unittest.TestCase):
    def _custom_db(self):
        folder = tempfile.TemporaryDirectory()
        path = Path(folder.name) / "behavior.db"
        con = sqlite3.connect(path)
        con.executescript("""
            CREATE TABLE ingredients (
                ingredient_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE ko_behavior_families (
                family_id INTEGER PRIMARY KEY, family_code TEXT NOT NULL UNIQUE,
                family_name TEXT NOT NULL, role TEXT NOT NULL,
                description TEXT NOT NULL, physical_traits TEXT, verified INTEGER DEFAULT 0
            );
            CREATE TABLE ko_family_methods (
                family_method_id INTEGER PRIMARY KEY, family_id INTEGER NOT NULL,
                method_name TEXT NOT NULL, form_name TEXT NOT NULL DEFAULT '',
                cooking_environment TEXT NOT NULL, creates_environment TEXT,
                prep_minutes INTEGER, cook_minutes INTEGER, active_minutes INTEGER,
                attention_load REAL, equipment_name TEXT, add_stage TEXT,
                desired_outcome TEXT NOT NULL, handling_template TEXT,
                instruction_template TEXT NOT NULL, doneness_cue TEXT NOT NULL,
                failure_mode TEXT NOT NULL, recovery_hint TEXT NOT NULL,
                holdability TEXT, verified INTEGER DEFAULT 0,
                UNIQUE(family_id, method_name, form_name)
            );
            CREATE TABLE ingredient_behavior_memberships (
                membership_id INTEGER PRIMARY KEY, ingredient_id INTEGER NOT NULL,
                family_id INTEGER NOT NULL, form_name TEXT NOT NULL DEFAULT '',
                priority INTEGER, is_primary INTEGER, notes TEXT, verified INTEGER,
                UNIQUE(ingredient_id, family_id, form_name)
            );
            CREATE TABLE ko_ingredient_exceptions (
                exception_id INTEGER PRIMARY KEY, ingredient_id INTEGER NOT NULL,
                form_name TEXT NOT NULL DEFAULT '', method_name TEXT NOT NULL DEFAULT '',
                field_name TEXT NOT NULL, override_value TEXT NOT NULL,
                reason TEXT NOT NULL, verified INTEGER DEFAULT 0,
                UNIQUE(ingredient_id, form_name, method_name, field_name)
            );
        """)
        return folder, path, con

    def test_new_ingredient_inherits_existing_family_without_name_patch(self):
        folder, path, con = self._custom_db()
        try:
            seed_behavior_library(con)
            con.execute("INSERT INTO ingredients VALUES (1, 'Romanesco')")
            family_id = con.execute(
                "SELECT family_id FROM ko_behavior_families WHERE family_code='cruciferous'"
            ).fetchone()[0]
            con.execute(
                """INSERT INTO ingredient_behavior_memberships
                   VALUES (NULL, 1, ?, '', 100, 1, 'trained', 1)""", (family_id,)
            )
            con.commit()
            behavior = resolve_behavior("Romanesco", "vegetable", "Fresh", "skillet", path)
            self.assertEqual(behavior.source, "ckb_membership")
            self.assertEqual(behavior.primary_family.code, "cruciferous")
            self.assertIn("fork", behavior.method.doneness_cue.lower())
        finally:
            con.close()
            folder.cleanup()

    def test_verified_ingredient_exception_overrides_only_that_ingredient(self):
        folder, path, con = self._custom_db()
        try:
            seed_behavior_library(con)
            con.execute("INSERT INTO ingredients VALUES (1, 'Romanesco')")
            family_id = con.execute(
                "SELECT family_id FROM ko_behavior_families WHERE family_code='cruciferous'"
            ).fetchone()[0]
            con.execute(
                "INSERT INTO ingredient_behavior_memberships VALUES (NULL,1,?,'',100,1,'trained',1)",
                (family_id,),
            )
            con.execute(
                """INSERT INTO ko_ingredient_exceptions
                   VALUES (NULL,1,'Fresh','saute_steam','cook_minutes','9',
                           'Romanesco heads are unusually large',1)"""
            )
            con.commit()
            behavior = resolve_behavior("Romanesco", "vegetable", "Fresh", "skillet", path)
            self.assertEqual(behavior.method.cook_minutes, 9)
        finally:
            con.close()
            folder.cleanup()

    def test_form_changes_legume_operation(self):
        canned = resolve_behavior("Navy beans", "foundation", "Canned", "skillet", DB_PATH)
        dry = resolve_behavior("Navy beans", "foundation", "Dry", "skillet", DB_PATH)
        self.assertEqual(canned.method.method, "reheat")
        self.assertEqual(dry.method.method, "simmer")
        self.assertGreater(dry.method.cook_minutes, canned.method.cook_minutes)

    def test_incompatible_environment_is_not_disguised_as_generic_cooking(self):
        report = audit_behavior("Beef stew meat", "protein", "Fresh Raw", "skillet", DB_PATH)
        self.assertEqual(report.status, "conditional")
        self.assertIn("form- and environment-compatible method", report.missing)

    def test_real_selectable_catalog_is_classified(self):
        con = sqlite3.connect(DB_PATH)
        try:
            groups = [
                ("protein", "SELECT i.name FROM proteins p JOIN ingredients i USING(ingredient_id)"),
                ("vegetable", "SELECT i.name FROM vegetables v JOIN ingredients i USING(ingredient_id)"),
                ("vegetable", "SELECT name FROM ingredients WHERE active=1 AND lower(category)='fruit'"),
                ("foundation", "SELECT name FROM foundations WHERE verified=1"),
            ]
            missing = []
            for role, query in groups:
                for (name,) in con.execute(query):
                    if name == "Centauran Gotlet Ribs":
                        continue
                    if not family_codes_for(name, role, db_path=DB_PATH)[0]:
                        missing.append(name)
            self.assertEqual(missing, [])
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()
