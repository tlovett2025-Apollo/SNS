import csv
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ckb_training import (
    TRAINING_COLUMNS, import_training_rows, validate_alpha_gal_classification,
    validate_training_file,
)
from schema import create_schema

DB_PATH = Path(r"data\ckb_seed_001.db")

INGREDIENT_COLUMNS = [
    "name",
    "category",
    "default_storage",
    "dairy_flag",
    "gluten_flag",
    "pork_flag",
    "egg_flag",
    "notes",
    "display_order",
    "verified",
    "walmart_common",
    "freeze_dryable",
]

PROTEIN_COLUMNS = [
    "ingredient_name",
    "protein_group",
    "cost_level",
    "energy_level",
    "animal_source",
    "meat_color",
    "alpha_gal_safe",
    "default_prep",
    "default_cook_temp_f",
    "lean_flag",
    "freezer_friendly",
    "freeze_dry_friendly",
    "default_serving_oz",
    "verified",
    "notes",
]

VEGETABLE_COLUMNS = [
    "ingredient_name",
    "vegetable_group",
    "soft_texture_possible",
    "cooks_fast",
    "frozen_available",
    "canned_available",
    "freeze_dry_friendly",
    "default_cook_time",
    "verified",
    "notes",
]

FOUNDATION_COLUMNS = [
    "name",
    "foundation_type",
    "texture",
    "pantry_style",
    "energy_level",
    "good_with_gravy",
    "good_with_sauce",
    "notes",
    "ingredient_name",
    "default_portion",
    "gluten_free",
    "freeze_dry_friendly",
    "default_cook_time",
    "verified",
]

# Techniques are intentionally flexible because the table schema may evolve.
# Required CSV column: name
# Optional columns are imported when the matching DB column exists.
TECHNIQUE_REQUIRED_COLUMNS = ["name"]


rows_cache = []
validation_ok = False
current_preview_columns = ()


def int_flag(value):
    value = str(value).strip().lower()
    return 1 if value in ["1", "yes", "true", "y", "x"] else 0


def optional_int(value):
    value = str(value).strip()
    if value == "":
        return None
    return int(value)


def optional_float(value):
    value = str(value).strip()
    if value == "":
        return None
    return float(value)


def clean_text(value):
    return str(value).strip()


def backup_database():
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"ckb_seed_001_backup_{stamp}.db"
    shutil.copy(DB_PATH, backup_path)
    return backup_path


def ensure_training_schema():
    """Apply additive training migrations only after preserving the current CKB."""
    con = sqlite3.connect(DB_PATH)
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    state_columns = {row[1] for row in con.execute("PRAGMA table_info(ingredient_states)")}
    ingredient_columns = {row[1] for row in con.execute("PRAGMA table_info(ingredients)")}
    con.close()
    required_tables = {"ko_profiles", "ko_activities", "ckb_change_log"}
    required_state_columns = {"active_minutes", "passive_minutes", "attention_score", "holdability", "verified"}
    if required_tables <= tables and required_state_columns <= state_columns and "knowledge_status" in ingredient_columns:
        return None
    backup_path = backup_database()
    create_schema()
    return backup_path


def get_ckb_counts():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    counts = {}
    for table in ["ingredients", "proteins", "vegetables", "foundations", "sauces", "techniques", "signature_recipes", "ingredient_forms", "ingredient_states", "ko_profiles", "ko_activities"]:
        try:
            counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            counts[table] = "?"
    con.close()
    return counts


def get_table_columns(cur, table_name):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table_name})").fetchall()]


def require_columns(reader, required_columns, label):
    missing = [c for c in required_columns if c not in reader.fieldnames]
    if missing:
        raise ValueError(f"Missing {label} columns: {missing}")


def get_ingredient_id_by_name(cur, ingredient_name, required=True):
    ingredient_name = clean_text(ingredient_name)
    if not ingredient_name:
        if required:
            raise ValueError("Blank ingredient_name.")
        return None

    found = cur.execute(
        "SELECT ingredient_id FROM ingredients WHERE lower(name)=lower(?)",
        (ingredient_name,)
    ).fetchone()

    if not found:
        raise ValueError(f"Ingredient not found in CKB: {ingredient_name}")

    return found[0]


def load_rows_generic(csv_path, required_columns, unique_column, label):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        require_columns(reader, required_columns, label)
        rows = list(reader)

    seen = set()
    duplicates = []

    for i, row in enumerate(rows, start=2):
        value = clean_text(row.get(unique_column, ""))
        if not value:
            raise ValueError(f"Blank {unique_column} on CSV row {i}.")

        key = value.lower()
        if key in seen:
            duplicates.append(value)
        seen.add(key)

    return rows, duplicates


def validate_ingredients(csv_path):
    rows, duplicate_names = load_rows_generic(csv_path, INGREDIENT_COLUMNS, "name", "ingredient")
    seen_orders = set()
    duplicate_orders = []

    for i, row in enumerate(rows, start=2):
        try:
            display_order = int(row["display_order"])
        except Exception:
            raise ValueError(f"Invalid display_order on CSV row {i}: {row['display_order']}")

        if display_order in seen_orders:
            duplicate_orders.append(display_order)
        seen_orders.add(display_order)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    existing_names = []
    existing_orders = []

    for row in rows:
        name = clean_text(row["name"])
        display_order = int(row["display_order"])

        if cur.execute("SELECT ingredient_id FROM ingredients WHERE lower(name)=lower(?)", (name,)).fetchone():
            existing_names.append(name)

        found_order = cur.execute(
            "SELECT ingredient_id, name FROM ingredients WHERE display_order=?",
            (display_order,)
        ).fetchone()

        if found_order:
            existing_orders.append((display_order, found_order[1]))

    con.close()

    problems = []
    if duplicate_names:
        problems.append(f"CSV duplicate names: {len(duplicate_names)}")
    if duplicate_orders:
        problems.append(f"CSV duplicate display_order values: {len(duplicate_orders)}")
    if existing_names:
        problems.append(f"Already in CKB by name: {len(existing_names)}")
    if existing_orders:
        problems.append(f"Already in CKB by display_order: {len(existing_orders)}")

    return rows, problems


def validate_proteins(csv_path):
    rows, duplicate_names = load_rows_generic(csv_path, PROTEIN_COLUMNS, "ingredient_name", "protein")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    existing = []
    missing_ingredients = []

    for row_number, row in enumerate(rows, start=2):
        ingredient_name = clean_text(row["ingredient_name"])
        try:
            ingredient_id = get_ingredient_id_by_name(cur, ingredient_name, required=True)
        except ValueError:
            missing_ingredients.append(ingredient_name)
            continue

        if cur.execute("SELECT protein_id FROM proteins WHERE ingredient_id=?", (ingredient_id,)).fetchone():
            existing.append(ingredient_name)

        # Data type checks
        optional_int(row["default_cook_temp_f"])
        optional_float(row["default_serving_oz"])
        try:
            validate_alpha_gal_classification(
                ingredient_name, row["animal_source"], row["alpha_gal_safe"], row_number
            )
        except ValueError:
            con.close()
            raise

    con.close()

    problems = []
    if duplicate_names:
        problems.append(f"CSV duplicate ingredient_name values: {len(duplicate_names)}")
    if missing_ingredients:
        problems.append(f"Ingredients not found in CKB: {len(missing_ingredients)}")
    if existing:
        problems.append(f"Already in proteins table: {len(existing)}")

    return rows, problems


def validate_vegetables(csv_path):
    rows, duplicate_names = load_rows_generic(csv_path, VEGETABLE_COLUMNS, "ingredient_name", "vegetable")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    existing = []
    missing_ingredients = []

    for row in rows:
        ingredient_name = clean_text(row["ingredient_name"])
        try:
            ingredient_id = get_ingredient_id_by_name(cur, ingredient_name, required=True)
        except ValueError:
            missing_ingredients.append(ingredient_name)
            continue

        if cur.execute("SELECT vegetable_id FROM vegetables WHERE ingredient_id=?", (ingredient_id,)).fetchone():
            existing.append(ingredient_name)

        optional_int(row["default_cook_time"])

    con.close()

    problems = []
    if duplicate_names:
        problems.append(f"CSV duplicate ingredient_name values: {len(duplicate_names)}")
    if missing_ingredients:
        problems.append(f"Ingredients not found in CKB: {len(missing_ingredients)}")
    if existing:
        problems.append(f"Already in vegetables table: {len(existing)}")

    return rows, problems


def validate_foundations(csv_path):
    rows, duplicate_names = load_rows_generic(csv_path, FOUNDATION_COLUMNS, "name", "foundation")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    existing = []
    missing_ingredients = []

    for row in rows:
        name = clean_text(row["name"])
        ingredient_name = clean_text(row.get("ingredient_name", ""))

        if cur.execute("SELECT foundation_id FROM foundations WHERE lower(name)=lower(?)", (name,)).fetchone():
            existing.append(name)

        if ingredient_name:
            try:
                get_ingredient_id_by_name(cur, ingredient_name, required=False)
            except ValueError:
                missing_ingredients.append(ingredient_name)

        optional_int(row["default_cook_time"])

    con.close()

    problems = []
    if duplicate_names:
        problems.append(f"CSV duplicate foundation names: {len(duplicate_names)}")
    if missing_ingredients:
        problems.append(f"Linked ingredients not found in CKB: {len(missing_ingredients)}")
    if existing:
        problems.append(f"Already in foundations table: {len(existing)}")

    return rows, problems


def validate_techniques(csv_path):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        require_columns(reader, TECHNIQUE_REQUIRED_COLUMNS, "technique")
        rows = list(reader)

    seen = set()
    duplicates = []

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    technique_cols = get_table_columns(cur, "techniques")

    if "name" not in technique_cols:
        con.close()
        raise ValueError("The techniques table does not have a 'name' column. Please inspect the schema before importing techniques.")

    existing = []

    for i, row in enumerate(rows, start=2):
        name = clean_text(row["name"])
        if not name:
            raise ValueError(f"Blank technique name on CSV row {i}.")

        key = name.lower()
        if key in seen:
            duplicates.append(name)
        seen.add(key)

        if cur.execute("SELECT technique_id FROM techniques WHERE lower(name)=lower(?)", (name,)).fetchone():
            existing.append(name)

    con.close()

    problems = []
    if duplicates:
        problems.append(f"CSV duplicate technique names: {len(duplicates)}")
    if existing:
        problems.append(f"Already in techniques table: {len(existing)}")

    return rows, problems


def import_ingredients(rows):
    backup_path = backup_database()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    imported = 0
    skipped = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for row in rows:
        name = clean_text(row["name"])
        search_name = name.lower()

        if cur.execute("SELECT ingredient_id FROM ingredients WHERE lower(name)=lower(?)", (name,)).fetchone():
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO ingredients
            (
                name, category, default_storage, dairy_flag, gluten_flag, pork_flag,
                egg_flag, active, notes, display_order, search_name, created_date,
                modified_date, verified, walmart_common, freeze_dryable
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                clean_text(row["category"]),
                clean_text(row["default_storage"]),
                int_flag(row["dairy_flag"]),
                int_flag(row["gluten_flag"]),
                int_flag(row["pork_flag"]),
                int_flag(row["egg_flag"]),
                1,
                clean_text(row["notes"]),
                int(row["display_order"]),
                search_name,
                now,
                now,
                int_flag(row["verified"]),
                int_flag(row["walmart_common"]),
                int_flag(row["freeze_dryable"]),
            )
        )
        imported += 1

    con.commit()
    con.close()
    return imported, skipped, backup_path


def import_proteins(rows):
    backup_path = backup_database()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    imported = 0
    skipped = 0

    for row in rows:
        ingredient_id = get_ingredient_id_by_name(cur, row["ingredient_name"], required=True)

        if cur.execute("SELECT protein_id FROM proteins WHERE ingredient_id=?", (ingredient_id,)).fetchone():
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO proteins
            (
                ingredient_id, default_technique_id, cost_level, energy_level, animal_source,
                meat_color, alpha_gal_safe, default_prep, notes, protein_group,
                default_cook_temp_f, lean_flag, freezer_friendly, freeze_dry_friendly,
                default_serving_oz, verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ingredient_id,
                None,
                clean_text(row["cost_level"]),
                clean_text(row["energy_level"]),
                clean_text(row["animal_source"]),
                clean_text(row["meat_color"]),
                int_flag(row["alpha_gal_safe"]),
                clean_text(row["default_prep"]),
                clean_text(row["notes"]),
                clean_text(row["protein_group"]),
                optional_int(row["default_cook_temp_f"]),
                int_flag(row["lean_flag"]),
                int_flag(row["freezer_friendly"]),
                int_flag(row["freeze_dry_friendly"]),
                optional_float(row["default_serving_oz"]) or 4.0,
                int_flag(row["verified"]),
            )
        )
        imported += 1

    con.commit()
    con.close()
    return imported, skipped, backup_path


def import_vegetables(rows):
    backup_path = backup_database()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    imported = 0
    skipped = 0

    for row in rows:
        ingredient_id = get_ingredient_id_by_name(cur, row["ingredient_name"], required=True)

        if cur.execute("SELECT vegetable_id FROM vegetables WHERE ingredient_id=?", (ingredient_id,)).fetchone():
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO vegetables
            (
                ingredient_id, common_prep_id, soft_texture_possible, cooks_fast,
                notes, vegetable_group, frozen_available, canned_available,
                freeze_dry_friendly, default_cook_time, verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ingredient_id,
                None,
                int_flag(row["soft_texture_possible"]),
                int_flag(row["cooks_fast"]),
                clean_text(row["notes"]),
                clean_text(row["vegetable_group"]),
                int_flag(row["frozen_available"]),
                int_flag(row["canned_available"]),
                int_flag(row["freeze_dry_friendly"]),
                optional_int(row["default_cook_time"]),
                int_flag(row["verified"]),
            )
        )
        imported += 1

    con.commit()
    con.close()
    return imported, skipped, backup_path


def import_foundations(rows):
    backup_path = backup_database()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    imported = 0
    skipped = 0

    for row in rows:
        name = clean_text(row["name"])

        if cur.execute("SELECT foundation_id FROM foundations WHERE lower(name)=lower(?)", (name,)).fetchone():
            skipped += 1
            continue

        ingredient_name = clean_text(row.get("ingredient_name", ""))
        ingredient_id = get_ingredient_id_by_name(cur, ingredient_name, required=False) if ingredient_name else None

        cur.execute(
            """
            INSERT INTO foundations
            (
                name, foundation_type, texture, pantry_style, energy_level,
                good_with_gravy, good_with_sauce, notes, ingredient_id,
                default_portion, gluten_free, freeze_dry_friendly,
                default_cook_time, verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                clean_text(row["foundation_type"]),
                clean_text(row["texture"]),
                clean_text(row["pantry_style"]),
                clean_text(row["energy_level"]),
                int_flag(row["good_with_gravy"]),
                int_flag(row["good_with_sauce"]),
                clean_text(row["notes"]),
                ingredient_id,
                clean_text(row["default_portion"]),
                int_flag(row["gluten_free"]),
                int_flag(row["freeze_dry_friendly"]),
                optional_int(row["default_cook_time"]),
                int_flag(row["verified"]),
            )
        )
        imported += 1

    con.commit()
    con.close()
    return imported, skipped, backup_path


def import_techniques(rows):
    backup_path = backup_database()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    technique_cols = get_table_columns(cur, "techniques")
    pk_cols = {"technique_id"}
    importable_cols = [c for c in technique_cols if c not in pk_cols and c in rows[0].keys()]

    if "name" not in importable_cols:
        con.close()
        raise ValueError("Technique CSV must include a name column, and the techniques table must contain a name column.")

    imported = 0
    skipped = 0

    for row in rows:
        name = clean_text(row["name"])

        if cur.execute("SELECT technique_id FROM techniques WHERE lower(name)=lower(?)", (name,)).fetchone():
            skipped += 1
            continue

        values = []
        cols = []

        for col in importable_cols:
            value = row[col]
            # Basic integer normalization for common flag/time fields.
            if col.endswith("_flag") or col in ["verified", "active"]:
                value = int_flag(value)
            elif col.endswith("_minutes") or col.endswith("_time") or col.endswith("_time_minutes"):
                value = optional_int(value)
            else:
                value = clean_text(value)

            cols.append(col)
            values.append(value)

        placeholders = ", ".join(["?"] * len(cols))
        col_sql = ", ".join(cols)

        cur.execute(
            f"INSERT INTO techniques ({col_sql}) VALUES ({placeholders})",
            values
        )

        imported += 1

    con.commit()
    con.close()
    return imported, skipped, backup_path


def get_import_type():
    return import_type_var.get()


def validate_selected_file(csv_path, import_type):
    if import_type in TRAINING_COLUMNS:
        return validate_training_file(csv_path, import_type, DB_PATH)
    if import_type == "Ingredients":
        return validate_ingredients(csv_path)
    if import_type == "Proteins":
        return validate_proteins(csv_path)
    if import_type == "Vegetables":
        return validate_vegetables(csv_path)
    if import_type == "Foundations":
        return validate_foundations(csv_path)
    if import_type == "Techniques":
        return validate_techniques(csv_path)
    raise ValueError(f"Unsupported import type: {import_type}")


def import_selected_rows(rows, import_type):
    if import_type in TRAINING_COLUMNS:
        backup_path = backup_database()
        imported, skipped = import_training_rows(rows, import_type, DB_PATH)
        return imported, skipped, backup_path
    if import_type == "Ingredients":
        return import_ingredients(rows)
    if import_type == "Proteins":
        return import_proteins(rows)
    if import_type == "Vegetables":
        return import_vegetables(rows)
    if import_type == "Foundations":
        return import_foundations(rows)
    if import_type == "Techniques":
        return import_techniques(rows)
    raise ValueError(f"Unsupported import type: {import_type}")


def refresh_counts():
    counts = get_ckb_counts()
    count_text.set(
        f"CKB Counts — Ingredients: {counts['ingredients']} | "
        f"Proteins: {counts['proteins']} | Vegetables: {counts['vegetables']} | "
        f"Foundations: {counts['foundations']} | Sauces: {counts['sauces']} | "
        f"Techniques: {counts['techniques']} | Recipes: {counts['signature_recipes']}"
        f" | Forms: {counts['ingredient_forms']} | States: {counts['ingredient_states']}"
        f" | KO Profiles: {counts['ko_profiles']} | KO Activities: {counts['ko_activities']}"
    )


def browse_file():
    path = filedialog.askopenfilename(
        title=f"Choose {get_import_type()} Wave CSV",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if path:
        csv_path_var.set(path)
        import_button.config(state="disabled")
        status_var.set("CSV selected. Click Validate.")
        preview_table.delete(*preview_table.get_children())


def reset_preview_columns(columns, headings=None, widths=None):
    global current_preview_columns

    current_preview_columns = tuple(columns)
    preview_table.config(columns=current_preview_columns)

    for col in current_preview_columns:
        heading = headings.get(col, col) if headings else col
        width = widths.get(col, 120) if widths else 120
        preview_table.heading(col, text=heading)
        preview_table.column(col, width=width)

    # Remove headings for any old columns no longer present.
    preview_table.delete(*preview_table.get_children())


def set_preview_for_import_type(import_type):
    if import_type == "Ingredients":
        columns = (
            "display_order", "name", "category", "default_storage",
            "dairy_flag", "gluten_flag", "pork_flag", "egg_flag",
            "verified", "walmart_common", "freeze_dryable", "notes"
        )
        headings = {
            "display_order": "Order",
            "name": "Name",
            "category": "Category",
            "default_storage": "Storage",
            "dairy_flag": "Dairy",
            "gluten_flag": "Gluten",
            "pork_flag": "Pork",
            "egg_flag": "Egg",
            "verified": "Verified",
            "walmart_common": "Walmart",
            "freeze_dryable": "FD",
            "notes": "Notes",
        }
        widths = {
            "display_order": 65, "name": 180, "category": 120,
            "default_storage": 90, "dairy_flag": 55, "gluten_flag": 60,
            "pork_flag": 55, "egg_flag": 55, "verified": 70,
            "walmart_common": 75, "freeze_dryable": 55, "notes": 370,
        }
    elif import_type == "Proteins":
        columns = (
            "ingredient_name", "protein_group", "cost_level", "energy_level",
            "animal_source", "meat_color", "alpha_gal_safe", "default_prep",
            "default_cook_temp_f", "lean_flag", "freezer_friendly",
            "freeze_dry_friendly", "default_serving_oz", "verified", "notes"
        )
        headings = {
            "ingredient_name": "Ingredient", "protein_group": "Protein Group",
            "cost_level": "Cost", "energy_level": "Energy",
            "animal_source": "Animal Source", "meat_color": "Meat Color",
            "alpha_gal_safe": "Alpha-Gal", "default_prep": "Default Prep",
            "default_cook_temp_f": "Temp F", "lean_flag": "Lean",
            "freezer_friendly": "Freezer", "freeze_dry_friendly": "FD",
            "default_serving_oz": "Serving oz", "verified": "Verified",
            "notes": "Notes",
        }
        widths = {
            "ingredient_name": 160, "protein_group": 110, "cost_level": 80,
            "energy_level": 80, "animal_source": 100, "meat_color": 80,
            "alpha_gal_safe": 75, "default_prep": 140,
            "default_cook_temp_f": 70, "lean_flag": 55,
            "freezer_friendly": 65, "freeze_dry_friendly": 55,
            "default_serving_oz": 80, "verified": 70, "notes": 300,
        }
    elif import_type == "Vegetables":
        columns = (
            "ingredient_name", "vegetable_group", "soft_texture_possible",
            "cooks_fast", "frozen_available", "canned_available",
            "freeze_dry_friendly", "default_cook_time", "verified", "notes"
        )
        headings = {
            "ingredient_name": "Ingredient", "vegetable_group": "Veg Group",
            "soft_texture_possible": "Soft", "cooks_fast": "Fast",
            "frozen_available": "Frozen", "canned_available": "Canned",
            "freeze_dry_friendly": "FD", "default_cook_time": "Cook Min",
            "verified": "Verified", "notes": "Notes",
        }
        widths = {
            "ingredient_name": 180, "vegetable_group": 130,
            "soft_texture_possible": 65, "cooks_fast": 60,
            "frozen_available": 70, "canned_available": 70,
            "freeze_dry_friendly": 55, "default_cook_time": 80,
            "verified": 70, "notes": 500,
        }
    elif import_type == "Foundations":
        columns = (
            "name", "foundation_type", "texture", "pantry_style",
            "energy_level", "good_with_gravy", "good_with_sauce",
            "ingredient_name", "default_portion", "gluten_free",
            "freeze_dry_friendly", "default_cook_time", "verified", "notes"
        )
        headings = {
            "name": "Name", "foundation_type": "Type", "texture": "Texture",
            "pantry_style": "Pantry Style", "energy_level": "Energy",
            "good_with_gravy": "Gravy", "good_with_sauce": "Sauce",
            "ingredient_name": "Ingredient Link", "default_portion": "Portion",
            "gluten_free": "GF", "freeze_dry_friendly": "FD",
            "default_cook_time": "Cook Min", "verified": "Verified",
            "notes": "Notes",
        }
        widths = {
            "name": 160, "foundation_type": 110, "texture": 100,
            "pantry_style": 110, "energy_level": 75, "good_with_gravy": 65,
            "good_with_sauce": 65, "ingredient_name": 150,
            "default_portion": 100, "gluten_free": 55,
            "freeze_dry_friendly": 55, "default_cook_time": 80,
            "verified": 70, "notes": 330,
        }
    elif import_type == "Techniques":
        columns = ("name", "technique_type", "energy_level", "default_time_minutes", "verified", "notes")
        headings = {
            "name": "Name", "technique_type": "Type",
            "energy_level": "Energy", "default_time_minutes": "Time Min",
            "verified": "Verified", "notes": "Notes",
        }
        widths = {
            "name": 180, "technique_type": 140, "energy_level": 90,
            "default_time_minutes": 90, "verified": 70, "notes": 650,
        }
    else:
        columns = tuple(TRAINING_COLUMNS[import_type])
        headings = {column: column.replace("_", " ").title() for column in columns}
        widths = {
            column: (360 if column in {"instruction", "notes", "reason", "handling_note", "timing_note", "cooking_note", "desired_outcome", "failure_mode", "recovery_hint", "teaching_note"} else 120)
            for column in columns
        }

    reset_preview_columns(columns, headings, widths)


def on_import_type_changed(event=None):
    import_button.config(state="disabled")
    status_var.set(f"Import type changed to {get_import_type()}. Choose a CSV and validate.")
    csv_path_var.set("")
    set_preview_for_import_type(get_import_type())


def validate_file():
    global rows_cache, validation_ok

    validation_ok = False
    rows_cache = []
    import_button.config(state="disabled")
    preview_table.delete(*preview_table.get_children())

    csv_path = csv_path_var.get().strip()
    import_type = get_import_type()

    if not csv_path:
        messagebox.showerror("Missing CSV", "Choose a CSV file first.")
        return

    try:
        rows, problems = validate_selected_file(csv_path, import_type)
        rows_cache = rows

        # Ensure preview columns fit selected type before adding rows.
        set_preview_for_import_type(import_type)

        for row in rows:
            preview_table.insert(
                "",
                "end",
                values=tuple(clean_text(row.get(col, "")) for col in current_preview_columns),
            )

        if problems:
            validation_ok = False
            status_var.set(f"{import_type} validated with warnings: {len(rows)} rows | " + " | ".join(problems))
            messagebox.showwarning(
                "Validation Warnings",
                "The file loaded, but review these before importing:\n\n"
                + "\n".join(problems)
                + "\n\nImport is disabled until the wave is clean."
            )
            return

        validation_ok = True
        status_var.set(f"{import_type} validated clean: {len(rows)} rows | Ready to import.")
        import_button.config(state="normal")

    except Exception as e:
        rows_cache = []
        validation_ok = False
        import_button.config(state="disabled")
        status_var.set("Validation failed.")
        messagebox.showerror("Validation Error", str(e))


def import_file():
    if not validation_ok or not rows_cache:
        messagebox.showerror("Not Ready", "Validate a clean CSV first.")
        return

    import_type = get_import_type()

    confirm = messagebox.askyesno(
        "Confirm Import",
        f"Import {len(rows_cache)} {import_type.lower()} rows into:\n\n{DB_PATH}\n\nA backup will be created first."
    )

    if not confirm:
        return

    try:
        imported, skipped, backup_path = import_selected_rows(rows_cache, import_type)
        refresh_counts()
        import_button.config(state="disabled")
        status_var.set(f"{import_type} import complete: {imported} imported | {skipped} skipped")
        messagebox.showinfo(
            "Import Complete",
            f"Import type: {import_type}\n"
            f"Imported: {imported}\n"
            f"Skipped existing: {skipped}\n\n"
            f"Backup:\n{backup_path}"
        )
    except Exception as e:
        status_var.set("Import failed.")
        messagebox.showerror("Import Error", str(e))


root = tk.Tk()
root.title("CKB Studio")
root.geometry("1350x700")

csv_path_var = tk.StringVar()
import_type_var = tk.StringVar(value="Ingredients")

status_var = tk.StringVar(value="Choose an import type and CSV file, then validate.")
count_text = tk.StringVar(value="")

title = tk.Label(root, text="CKB Studio", font=("Arial", 18, "bold"))
title.pack(pady=8)

db_label = tk.Label(root, text=f"Database: {DB_PATH}")
db_label.pack()

count_label = tk.Label(root, textvariable=count_text)
count_label.pack()

file_frame = tk.Frame(root)
file_frame.pack(fill="x", padx=20, pady=10)

csv_entry = tk.Entry(file_frame, textvariable=csv_path_var)
csv_entry.pack(side="left", fill="x", expand=True)

browse_button = tk.Button(file_frame, text="Browse", command=browse_file)
browse_button.pack(side="left", padx=5)

type_frame = tk.Frame(root)
type_frame.pack(pady=5)

tk.Label(type_frame, text="Import Type:").pack(side="left", padx=5)

import_type_box = ttk.Combobox(
    type_frame,
    textvariable=import_type_var,
    values=[
        "Ingredients", "Proteins", "Vegetables", "Foundations", "Techniques",
        "Ingredient Forms", "Ingredient States", "KO Profiles", "KO Activities",
        "Protein Safety Corrections",
        "Ingredient Form Corrections", "Ingredient Metadata Corrections",
    ],
    state="readonly",
    width=20
)
import_type_box.pack(side="left")
import_type_box.bind("<<ComboboxSelected>>", on_import_type_changed)

button_frame = tk.Frame(root)
button_frame.pack(pady=5)

validate_button = tk.Button(button_frame, text="Validate", width=15, command=validate_file)
validate_button.pack(side="left", padx=5)

import_button = tk.Button(button_frame, text="Import", width=15, command=import_file, state="disabled")
import_button.pack(side="left", padx=5)

refresh_button = tk.Button(button_frame, text="Refresh Counts", width=15, command=refresh_counts)
refresh_button.pack(side="left", padx=5)

exit_button = tk.Button(button_frame, text="Exit", width=15, command=root.destroy)
exit_button.pack(side="left", padx=5)

# Initial preview table; columns are reset by set_preview_for_import_type().
preview_table = ttk.Treeview(root, columns=(), show="headings", height=22)
preview_table.pack(fill="both", expand=True, padx=20, pady=10)

status_label = tk.Label(root, textvariable=status_var, anchor="w")
status_label.pack(fill="x", padx=20, pady=5)

schema_backup = ensure_training_schema()
if schema_backup:
    status_var.set(f"Training schema added safely. Pre-migration backup: {schema_backup}")
set_preview_for_import_type("Ingredients")
refresh_counts()
root.mainloop()
