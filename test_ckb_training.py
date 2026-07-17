import csv
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from ckb_training import (
    ACTIVITY_COLUMNS, BEHAVIOR_FAMILY_COLUMNS, BEHAVIOR_MEMBERSHIP_COLUMNS,
    FAMILY_METHOD_COLUMNS, FORM_COLUMNS, PROFILE_COLUMNS, STATE_COLUMNS,
    import_training_rows, validate_alpha_gal_classification, validate_training_file,
)
from ko_behavior import resolve_behavior
from schema import MIGRATIONS, SCHEMA_SQL


HERE = Path(__file__).resolve().parent

class CKBTrainingSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "test_ckb.db"
        shutil.copy(HERE / "data" / "ckb_seed_001.db", self.db_path)

        with closing(sqlite3.connect(self.db_path)) as con:
            con.executescript(SCHEMA_SQL)

            for table, column, sql in MIGRATIONS:
                columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
                if column not in columns:
                    con.execute(sql)

            target_names = (
                "Chicken breast",
                "White rice",
                "Mushrooms",
                "Asparagus",
                "Swiss chard",
                "Ground beef",
            )
            marks = ",".join("?" for _ in target_names)
            target_ids = [
                row[0]
                for row in con.execute(
                    f"SELECT ingredient_id FROM ingredients WHERE name IN ({marks})",
                    target_names,
                )
            ]

            # Remove dependent knowledge before removing forms and states.
            con.execute(
                """DELETE FROM ko_activities
                   WHERE component_name IN
                   ('Chicken breast','Rice','Mushrooms','Asparagus','Swiss chard','Ground beef')"""
            )
            con.execute(
                """DELETE FROM ko_profiles
                   WHERE component_name IN
                   ('Chicken breast','Rice','Mushrooms','Asparagus','Swiss chard','Ground beef')"""
            )

            if target_ids:
                id_marks = ",".join("?" for _ in target_ids)
                con.execute(
                    f"DELETE FROM user_inventory WHERE ingredient_id IN ({id_marks})",
                    target_ids,
                )
                con.execute(
                    f"DELETE FROM ingredient_forms WHERE ingredient_id IN ({id_marks})",
                    target_ids,
                )
                con.execute(
                    f"DELETE FROM ingredient_states WHERE ingredient_id IN ({id_marks})",
                    target_ids,
                )

            con.execute(
                "DELETE FROM ckb_change_log WHERE change_type='safety correction'"
            )
            con.execute(
                """UPDATE proteins SET alpha_gal_safe=1 WHERE ingredient_id IN
                   (SELECT ingredient_id FROM ingredients WHERE name IN
                   ('Beef brisket','Beef stew meat','Chuck roast','Corned beef',
                    'Flank steak','Ground beef','Ribeye steak','Sirloin steak'))"""
            )
            con.commit()

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_csv(self, name, columns, rows):
        path = Path(self.tempdir.name) / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _minimal_profile_row(self, ingredient_name="Chicken breast", attention_score="6"):
        return {
            "ingredient_name": ingredient_name, "role": "protein", "default_state": "Fresh Raw",
            "prep_minutes": "2", "cook_minutes": "10", "active_minutes": "6",
            "passive_minutes": "4", "attention_score": attention_score, "rest_minutes": "5",
            "add_stage": "middle", "holdability": "fair", "preferred_method": "cook",
            "desired_outcome": "Safely cooked and moist", "failure_mode": "Can dry out",
            "recovery_hint": "Serve with sauce", "teaching_note": "Check safe doneness",
            "parallel_ok": "0", "start_first": "0", "timing_note": "Cook near service",
            "handling_note": "Keep raw food separate", "cooking_note": "Cook safely",
            "work_score": "5", "cleanup_score": "4", "mental_load_score": "5", "verified": "1",
        }

    def _install_minimal_chicken_knowledge(self):
        waves = [
            ("Ingredient Forms", FORM_COLUMNS, [{"ingredient_name": "Chicken breast", "form_name": "Test Fresh Raw", "pantry_style": "fridge", "notes": "test"}]),
            ("Ingredient States", STATE_COLUMNS, [{"ingredient_name": "Chicken breast", "state_name": "Fresh Raw", "storage_location": "fridge", "needs_cooking": "1", "ready_to_eat": "0", "typical_prep_minutes": "2", "typical_cook_minutes": "10", "active_minutes": "6", "passive_minutes": "4", "attention_score": "6", "energy_level": "medium", "rank_penalty": "0", "holdability": "fair", "handling_note": "Keep separate", "timing_note": "Cook near service", "cooking_note": "Cook safely", "verified": "1", "notes": "test"}]),
            ("KO Profiles", PROFILE_COLUMNS, [self._minimal_profile_row()]),
            ("KO Activities", ACTIVITY_COLUMNS, [
                {"ingredient_name": "Chicken breast", "role": "protein", "state_name": "Fresh Raw", "sequence": "1", "activity_type": "prep", "instruction": "Prep Chicken breast safely.", "minutes": "2", "human_busy": "1", "attention_load": "1.0", "equipment_name": "counter", "stage": "middle", "parallel_ok": "1", "depends_on_sequence": "", "verified": "1"},
                {"ingredient_name": "Chicken breast", "role": "protein", "state_name": "Fresh Raw", "sequence": "2", "activity_type": "cook", "instruction": "Cook Chicken breast safely in a skillet.", "minutes": "10", "human_busy": "1", "attention_load": "0.5", "equipment_name": "burner", "stage": "middle", "parallel_ok": "0", "depends_on_sequence": "1", "verified": "1"},
            ]),
        ]
        counts = []
        for index, (import_type, columns, source_rows) in enumerate(waves):
            path = self._write_csv(f"fixture_{index}.csv", columns, source_rows)
            rows, problems = validate_training_file(path, import_type, self.db_path)
            self.assertEqual([], problems)
            counts.append(import_training_rows(rows, import_type, self.db_path)[0])
        return counts

    def test_all_first_training_waves_validate_and_import_in_order(self):
        self.assertEqual([1, 1, 1, 2], self._install_minimal_chicken_knowledge())

    def test_verified_ckb_profile_publishes_recipe_activities(self):
        self._install_minimal_chicken_knowledge()
        import ingredient_profiles
        original_path = ingredient_profiles.DB_PATH
        try:
            ingredient_profiles.DB_PATH = self.db_path
            chicken = ingredient_profiles.get_ingredient_profile("Chicken breast", "protein")
            chicken_kinds = [activity.activity_type for activity in chicken.publish_activities(state_name="Fresh Raw")]
        finally:
            ingredient_profiles.DB_PATH = original_path
        self.assertEqual(["prep", "cook", "verify", "rest"], chicken_kinds)

    def test_alpha_gal_wave_corrects_beef_and_writes_audit_rows(self):
        names = ["Beef brisket", "Beef stew meat", "Chuck roast", "Corned beef", "Flank steak", "Ground beef", "Ribeye steak", "Sirloin steak"]
        path = self._write_csv(
            "alpha_fixture.csv",
            ["ingredient_name", "alpha_gal_safe", "reason", "verified"],
            [{"ingredient_name": name, "alpha_gal_safe": "0", "reason": "Mammalian meat", "verified": "1"} for name in names],
        )
        rows, _ = validate_training_file(path, "Protein Safety Corrections", self.db_path)
        import_training_rows(rows, "Protein Safety Corrections", self.db_path)
        con = sqlite3.connect(self.db_path)
        unsafe_marked_safe = con.execute(
            """SELECT count(*) FROM proteins p JOIN ingredients i ON i.ingredient_id=p.ingredient_id
               WHERE i.category='Beef' AND p.alpha_gal_safe=1"""
        ).fetchone()[0]
        audit_rows = con.execute("SELECT count(*) FROM ckb_change_log").fetchone()[0]
        con.close()
        self.assertEqual(0, unsafe_marked_safe)
        self.assertEqual(8, audit_rows)

    def test_unverified_safety_correction_is_blocked(self):
        path = self._write_csv(
            "bad_safety.csv",
            ["ingredient_name", "alpha_gal_safe", "reason", "verified"],
            [{"ingredient_name": "Ground beef", "alpha_gal_safe": "0", "reason": "Mammalian meat", "verified": "0"}],
        )
        with self.assertRaisesRegex(ValueError, "must be verified"):
            validate_training_file(path, "Protein Safety Corrections", self.db_path)

    def test_future_mammal_protein_cannot_be_marked_alpha_gal_safe(self):
        with self.assertRaisesRegex(ValueError, "cannot be marked safe"):
            validate_alpha_gal_classification("Ground beef", "cattle", "1", 2)
        self.assertEqual(0, validate_alpha_gal_classification("Ground beef", "cattle", "0", 2))
        self.assertEqual(1, validate_alpha_gal_classification("Chicken breast", "chicken", "1", 2))

    def test_attention_score_outside_zero_to_ten_is_blocked(self):
        path = self._write_csv("bad_attention.csv", PROFILE_COLUMNS, [self._minimal_profile_row("Ground beef", "11")])
        with self.assertRaisesRegex(ValueError, "attention_score must be 0–10"):
            validate_training_file(path, "KO Profiles", self.db_path)

    def test_import_rolls_back_every_row_if_a_later_row_fails(self):
        rows = [
            {"ingredient_name": "Chicken breast", "form_name": "Test form", "pantry_style": "fridge", "notes": ""},
            {"ingredient_name": "Ingredient that does not exist", "form_name": "Bad form", "pantry_style": "pantry", "notes": ""},
        ]
        with closing(sqlite3.connect(self.db_path)) as con:
            before = con.execute("SELECT count(*) FROM ingredient_forms").fetchone()[0]
        with self.assertRaises(ValueError):
            import_training_rows(rows, "Ingredient Forms", self.db_path)
        with closing(sqlite3.connect(self.db_path)) as con:
            after = con.execute("SELECT count(*) FROM ingredient_forms").fetchone()[0]
        self.assertEqual(before, after)

    def test_form_correction_deletes_exact_storage_label_and_audits_it(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            ingredient_id = con.execute(
                "SELECT ingredient_id FROM ingredients WHERE name='Black pepper'"
            ).fetchone()[0]
            if not con.execute(
                "SELECT 1 FROM ingredient_forms WHERE ingredient_id=? AND form_name='Pantry'",
                (ingredient_id,),
            ).fetchone():
                con.execute(
                    "INSERT INTO ingredient_forms (ingredient_id,form_name,pantry_style,notes) VALUES (?,'Pantry','pantry','test fixture')",
                    (ingredient_id,),
                )
                con.commit()
        path = self._write_csv(
            "form_correction.csv",
            ["ingredient_name", "form_name", "action", "reason", "verified"],
            [{"ingredient_name": "Black pepper", "form_name": "Pantry", "action": "delete",
              "reason": "Storage location is not a Form", "verified": "1"}],
        )
        rows, problems = validate_training_file(path, "Ingredient Form Corrections", self.db_path)
        self.assertEqual([], problems)
        self.assertEqual((1, 0), import_training_rows(rows, "Ingredient Form Corrections", self.db_path))
        with closing(sqlite3.connect(self.db_path)) as con:
            remaining = con.execute(
                """SELECT count(*) FROM ingredient_forms f JOIN ingredients i ON i.ingredient_id=f.ingredient_id
                   WHERE i.name='Black pepper' AND f.form_name='Pantry'"""
            ).fetchone()[0]
            audit = con.execute(
                "SELECT count(*) FROM ckb_change_log WHERE target_key='Black pepper' AND new_value='DELETED'"
            ).fetchone()[0]
        self.assertEqual(0, remaining)
        self.assertEqual(1, audit)

    def test_metadata_correction_marks_intentional_fictional_test_food(self):
        path = self._write_csv(
            "metadata_correction.csv",
            ["ingredient_name", "knowledge_status", "reason", "verified"],
            [{"ingredient_name": "Centauran Gotlet Ribs", "knowledge_status": "fictional_test",
              "reason": "Intentional test food", "verified": "1"}],
        )
        rows, _ = validate_training_file(path, "Ingredient Metadata Corrections", self.db_path)
        import_training_rows(rows, "Ingredient Metadata Corrections", self.db_path)
        with closing(sqlite3.connect(self.db_path)) as con:
            status = con.execute(
                "SELECT knowledge_status FROM ingredients WHERE name='Centauran Gotlet Ribs'"
            ).fetchone()[0]
        self.assertEqual("fictional_test", status)

    def test_family_method_and_membership_training_make_a_new_ko_operational(self):
        family_path = self._write_csv("family.csv", BEHAVIOR_FAMILY_COLUMNS, [{
            "family_code": "fictional_roast", "family_name": "Fictional roast",
            "role": "protein", "description": "A test roast family",
            "physical_traits": "large,raw", "verified": "1",
        }])
        rows, _ = validate_training_file(family_path, "Behavior Families", self.db_path)
        import_training_rows(rows, "Behavior Families", self.db_path)

        method_path = self._write_csv("method.csv", FAMILY_METHOD_COLUMNS, [{
            "family_code": "fictional_roast", "method_name": "roast",
            "form_name": "Fresh Raw", "cooking_environment": "preheated oven",
            "creates_environment": "roasting pan", "prep_minutes": "5",
            "cook_minutes": "40", "active_minutes": "5", "attention_load": ".2",
            "equipment_name": "oven", "add_stage": "early",
            "desired_outcome": "Tender slices", "handling_template": "Prepare {name}.",
            "instruction_template": "Roast {name} evenly.",
            "doneness_cue": "The verified fictional endpoint is reached.",
            "failure_mode": "It may remain tough.",
            "recovery_hint": "Continue roasting gently.", "holdability": "good",
            "verified": "1",
        }])
        rows, _ = validate_training_file(method_path, "Family Methods", self.db_path)
        import_training_rows(rows, "Family Methods", self.db_path)

        membership_path = self._write_csv("membership.csv", BEHAVIOR_MEMBERSHIP_COLUMNS, [{
            "ingredient_name": "Centauran Gotlet Ribs", "family_code": "fictional_roast",
            "form_name": "", "priority": "100", "is_primary": "1",
            "notes": "Importer contract test", "verified": "1",
        }])
        rows, _ = validate_training_file(
            membership_path, "Ingredient Behavior Memberships", self.db_path
        )
        import_training_rows(rows, "Ingredient Behavior Memberships", self.db_path)

        behavior = resolve_behavior(
            "Centauran Gotlet Ribs", "protein", "Fresh Raw", "roast", self.db_path
        )
        self.assertEqual("fictional_roast", behavior.primary_family.code)
        self.assertEqual(40, behavior.method.cook_minutes)


if __name__ == "__main__":
    unittest.main()
