import csv
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from ckb_training import (
    import_training_rows, validate_alpha_gal_classification, validate_training_file,
)
from schema import MIGRATIONS, SCHEMA_SQL


HERE = Path(__file__).resolve().parent

WAVES = [
    ("Protein Safety Corrections", HERE / "Wave005_ProteinSafety_AlphaGalCorrections.csv"),
    ("Ingredient Forms", HERE / "Wave006_IngredientForms_FirstTrainingSet.csv"),
    ("Ingredient States", HERE / "Wave007_IngredientStates_FirstTrainingSet.csv"),
    ("KO Profiles", HERE / "Wave008_KOProfiles_FirstTrainingSet.csv"),
    ("KO Activities", HERE / "Wave009_KOActivities_FirstTrainingSet.csv"),
]


class CKBTrainingSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "test_ckb.db"
        shutil.copy(HERE / "data" / "ckb_seed_001.db", self.db_path)
        con = sqlite3.connect(self.db_path)
        con.executescript(SCHEMA_SQL)
        for table, column, sql in MIGRATIONS:
            columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
            if column not in columns:
                con.execute(sql)
        target_names = ("Chicken breast", "White rice", "Mushrooms", "Asparagus", "Swiss chard")
        marks = ",".join("?" for _ in target_names)
        target_ids = [row[0] for row in con.execute(
            f"SELECT ingredient_id FROM ingredients WHERE name IN ({marks})", target_names
        )]
        if target_ids:
            id_marks = ",".join("?" for _ in target_ids)
            con.execute(f"DELETE FROM ingredient_forms WHERE ingredient_id IN ({id_marks})", target_ids)
            con.execute(f"DELETE FROM ingredient_states WHERE ingredient_id IN ({id_marks})", target_ids)
        con.execute("DELETE FROM ko_activities WHERE component_name IN ('Chicken breast','Rice','Mushrooms','Asparagus','Swiss chard')")
        con.execute("DELETE FROM ko_profiles WHERE component_name IN ('Chicken breast','Rice','Mushrooms','Asparagus','Swiss chard')")
        con.execute("DELETE FROM ckb_change_log WHERE change_type='safety correction'")
        con.execute(
            """UPDATE proteins SET alpha_gal_safe=1 WHERE ingredient_id IN
               (SELECT ingredient_id FROM ingredients WHERE name IN
               ('Beef brisket','Beef stew meat','Chuck roast','Corned beef','Flank steak','Ground beef','Ribeye steak','Sirloin steak'))"""
        )
        con.commit()
        con.close()

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_csv(self, name, columns, rows):
        path = Path(self.tempdir.name) / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_all_first_training_waves_validate_and_import_in_order(self):
        counts = []
        for import_type, path in WAVES:
            rows, problems = validate_training_file(path, import_type, self.db_path)
            self.assertEqual([], problems)
            imported, skipped = import_training_rows(rows, import_type, self.db_path)
            self.assertEqual(len(rows), imported)
            self.assertEqual(0, skipped)
            counts.append(imported)
        self.assertEqual([8, 12, 3, 5, 23], counts)

    def test_verified_ckb_profile_publishes_recipe_activities(self):
        for import_type, path in WAVES[1:]:
            rows, _ = validate_training_file(path, import_type, self.db_path)
            import_training_rows(rows, import_type, self.db_path)
        import ingredient_profiles
        original_path = ingredient_profiles.DB_PATH
        try:
            ingredient_profiles.DB_PATH = self.db_path
            chicken = ingredient_profiles.get_ingredient_profile("Chicken breast", "protein")
            rice = ingredient_profiles.get_ingredient_profile("Rice", "foundation")
            chicken_kinds = [activity.activity_type for activity in chicken.publish_activities(state_name="Fresh Raw")]
            rice_text = " ".join(activity.instruction for activity in rice.publish_activities())
        finally:
            ingredient_profiles.DB_PATH = original_path
        self.assertEqual(["prep", "cook", "rest", "slice"], chicken_kinds)
        self.assertIn("saucepan", rice_text)

    def test_alpha_gal_wave_corrects_beef_and_writes_audit_rows(self):
        rows, _ = validate_training_file(WAVES[0][1], WAVES[0][0], self.db_path)
        import_training_rows(rows, WAVES[0][0], self.db_path)
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
        with WAVES[3][1].open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            row = next(reader)
            columns = reader.fieldnames
        row["attention_score"] = "11"
        path = self._write_csv("bad_attention.csv", columns, [row])
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


if __name__ == "__main__":
    unittest.main()
