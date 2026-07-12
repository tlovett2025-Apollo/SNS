"""Validated CKB training-wave contracts and atomic import operations."""

import csv
import sqlite3
from datetime import datetime


FORM_COLUMNS = ["ingredient_name", "form_name", "pantry_style", "notes"]

STATE_COLUMNS = [
    "ingredient_name", "state_name", "storage_location", "needs_cooking",
    "ready_to_eat", "typical_prep_minutes", "typical_cook_minutes",
    "active_minutes", "passive_minutes", "attention_score", "energy_level",
    "rank_penalty", "holdability", "handling_note", "timing_note",
    "cooking_note", "verified", "notes",
]

PROFILE_COLUMNS = [
    "ingredient_name", "role", "default_state", "prep_minutes", "cook_minutes",
    "active_minutes", "passive_minutes", "attention_score", "rest_minutes",
    "add_stage", "holdability", "preferred_method", "desired_outcome",
    "failure_mode", "recovery_hint", "teaching_note", "parallel_ok",
    "start_first", "timing_note", "handling_note", "cooking_note",
    "work_score", "cleanup_score", "mental_load_score", "verified",
]

ACTIVITY_COLUMNS = [
    "ingredient_name", "role", "state_name", "sequence", "activity_type",
    "instruction", "minutes", "human_busy", "attention_load",
    "equipment_name", "stage", "parallel_ok", "depends_on_sequence", "verified",
]

PROTEIN_SAFETY_COLUMNS = [
    "ingredient_name", "alpha_gal_safe", "reason", "verified",
]

TRAINING_COLUMNS = {
    "Ingredient Forms": FORM_COLUMNS,
    "Ingredient States": STATE_COLUMNS,
    "KO Profiles": PROFILE_COLUMNS,
    "KO Activities": ACTIVITY_COLUMNS,
    "Protein Safety Corrections": PROTEIN_SAFETY_COLUMNS,
}

FLAG_VALUES = {"0", "1", "false", "true", "no", "yes", "n", "y"}
ROLES = {"protein", "vegetable", "foundation", "ingredient"}
STAGES = {"early", "middle", "late", "finish"}
ENERGY_LEVELS = {"", "very low", "low", "medium", "high"}
HOLDABILITY = {"", "poor", "fair", "good", "excellent"}
MAMMAL_SOURCES = {
    "cattle", "cow", "beef", "pig", "pork", "hog", "lamb", "sheep",
    "goat", "bison", "buffalo", "deer", "venison", "rabbit",
}


def clean(value):
    return "" if value is None else str(value).strip()


def flag(value, field, row_number):
    value = clean(value).lower()
    if value not in FLAG_VALUES:
        raise ValueError(f"Invalid {field} on CSV row {row_number}: {value!r}")
    return 1 if value in {"1", "true", "yes", "y"} else 0


def integer(value, field, row_number, minimum=0, maximum=None, optional=False):
    value = clean(value)
    if optional and value == "":
        return None
    try:
        result = int(value)
    except Exception as exc:
        raise ValueError(f"Invalid {field} on CSV row {row_number}: {value!r}") from exc
    if result < minimum or (maximum is not None and result > maximum):
        limit = f"{minimum}–{maximum}" if maximum is not None else f">= {minimum}"
        raise ValueError(f"{field} must be {limit} on CSV row {row_number}: {result}")
    return result


def decimal(value, field, row_number, minimum=0.0, maximum=None):
    try:
        result = float(clean(value))
    except Exception as exc:
        raise ValueError(f"Invalid {field} on CSV row {row_number}: {value!r}") from exc
    if result < minimum or (maximum is not None and result > maximum):
        limit = f"{minimum}–{maximum}" if maximum is not None else f">= {minimum}"
        raise ValueError(f"{field} must be {limit} on CSV row {row_number}: {result}")
    return result


def validate_alpha_gal_classification(ingredient_name, animal_source, safe_value, row_number):
    safe = flag(safe_value, "alpha_gal_safe", row_number)
    source = clean(animal_source).lower()
    if source in MAMMAL_SOURCES and safe:
        raise ValueError(
            f"Unsafe alpha-gal classification on CSV row {row_number}: "
            f"{clean(ingredient_name)} is mammalian ({source}) and cannot be marked safe."
        )
    return safe


def _read_rows(csv_path, columns):
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in columns if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        unexpected = [column for column in (reader.fieldnames or []) if column not in columns]
        if unexpected:
            raise ValueError(f"Unexpected columns: {unexpected}")
        rows = list(reader)
    if not rows:
        raise ValueError("Training CSV contains no data rows.")
    return rows


def _ingredient_id(cur, name, row_number):
    name = clean(name)
    found = cur.execute(
        "SELECT ingredient_id FROM ingredients WHERE lower(name)=lower(?)", (name,)
    ).fetchone()
    if not found:
        raise ValueError(f"Ingredient not found on CSV row {row_number}: {name}")
    return found[0]


def _component(cur, name, role, row_number):
    """Resolve an ingredient-backed component or a named foundation abstraction."""
    name = clean(name)
    found = cur.execute(
        "SELECT ingredient_id, name FROM ingredients WHERE lower(name)=lower(?)", (name,)
    ).fetchone()
    if found:
        return found[0], found[1]
    if role == "foundation":
        found = cur.execute(
            "SELECT name FROM foundations WHERE lower(name)=lower(?)", (name,)
        ).fetchone()
        if found:
            return None, found[0]
    raise ValueError(f"Component not found on CSV row {row_number}: {name} / {role}")


def _require_text(row, field, row_number):
    value = clean(row.get(field))
    if not value:
        raise ValueError(f"Blank {field} on CSV row {row_number}.")
    return value


def _reject_duplicates(keys, key, row_number):
    if key in keys:
        raise ValueError(f"Duplicate training key on CSV row {row_number}: {key}")
    keys.add(key)


def validate_training_file(csv_path, import_type, db_path):
    if import_type not in TRAINING_COLUMNS:
        raise ValueError(f"Unsupported training import type: {import_type}")
    rows = _read_rows(csv_path, TRAINING_COLUMNS[import_type])
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        seen = set()
        for row_number, row in enumerate(rows, start=2):
            ingredient_name = _require_text(row, "ingredient_name", row_number)
            ingredient_id = None
            if import_type not in {"KO Profiles", "KO Activities"}:
                ingredient_id = _ingredient_id(cur, ingredient_name, row_number)

            if import_type == "Ingredient Forms":
                form_name = _require_text(row, "form_name", row_number)
                key = (ingredient_name.lower(), form_name.lower())
                _reject_duplicates(seen, key, row_number)
                if cur.execute(
                    "SELECT 1 FROM ingredient_forms WHERE ingredient_id=? AND lower(form_name)=lower(?)",
                    (ingredient_id, form_name),
                ).fetchone():
                    raise ValueError(f"Ingredient form already exists on CSV row {row_number}: {ingredient_name} / {form_name}")

            elif import_type == "Ingredient States":
                state_name = _require_text(row, "state_name", row_number)
                key = (ingredient_name.lower(), state_name.lower())
                _reject_duplicates(seen, key, row_number)
                for field in ["needs_cooking", "ready_to_eat", "verified"]:
                    flag(row[field], field, row_number)
                for field in ["typical_prep_minutes", "typical_cook_minutes", "active_minutes", "passive_minutes", "rank_penalty"]:
                    integer(row[field], field, row_number)
                integer(row["attention_score"], "attention_score", row_number, 0, 10)
                if clean(row["energy_level"]).lower() not in ENERGY_LEVELS:
                    raise ValueError(f"Invalid energy_level on CSV row {row_number}: {row['energy_level']!r}")
                if clean(row["holdability"]).lower() not in HOLDABILITY:
                    raise ValueError(f"Invalid holdability on CSV row {row_number}: {row['holdability']!r}")
                if cur.execute(
                    "SELECT 1 FROM ingredient_states WHERE ingredient_id=? AND lower(state_name)=lower(?)",
                    (ingredient_id, state_name),
                ).fetchone():
                    raise ValueError(f"Ingredient state already exists on CSV row {row_number}: {ingredient_name} / {state_name}")

            elif import_type == "KO Profiles":
                role = _require_text(row, "role", row_number).lower()
                if role not in ROLES:
                    raise ValueError(f"Invalid role on CSV row {row_number}: {role!r}")
                ingredient_id, component_name = _component(cur, ingredient_name, role, row_number)
                key = (ingredient_name.lower(), role)
                _reject_duplicates(seen, key, row_number)
                for field in ["prep_minutes", "cook_minutes", "active_minutes", "passive_minutes", "rest_minutes"]:
                    integer(row[field], field, row_number)
                for field in ["attention_score", "work_score", "cleanup_score", "mental_load_score"]:
                    integer(row[field], field, row_number, 0, 10)
                for field in ["parallel_ok", "start_first", "verified"]:
                    flag(row[field], field, row_number)
                if clean(row["add_stage"]).lower() not in STAGES:
                    raise ValueError(f"Invalid add_stage on CSV row {row_number}: {row['add_stage']!r}")
                if clean(row["holdability"]).lower() not in HOLDABILITY:
                    raise ValueError(f"Invalid holdability on CSV row {row_number}: {row['holdability']!r}")
                if cur.execute("SELECT 1 FROM ko_profiles WHERE lower(component_name)=lower(?) AND role=?", (component_name, role)).fetchone():
                    raise ValueError(f"KO profile already exists on CSV row {row_number}: {ingredient_name} / {role}")

            elif import_type == "KO Activities":
                role = _require_text(row, "role", row_number).lower()
                if role not in ROLES:
                    raise ValueError(f"Invalid role on CSV row {row_number}: {role!r}")
                ingredient_id, component_name = _component(cur, ingredient_name, role, row_number)
                state_name = clean(row["state_name"])
                if not cur.execute(
                    "SELECT 1 FROM ko_profiles WHERE lower(component_name)=lower(?) AND role=?",
                    (component_name, role),
                ).fetchone():
                    raise ValueError(f"KO profile not found on CSV row {row_number}: {ingredient_name} / {role}")
                if state_name and not cur.execute(
                    "SELECT 1 FROM ingredient_states WHERE ingredient_id=? AND lower(state_name)=lower(?)",
                    (ingredient_id, state_name),
                ).fetchone():
                    raise ValueError(f"Ingredient state not found on CSV row {row_number}: {ingredient_name} / {state_name}")
                sequence = integer(row["sequence"], "sequence", row_number, 1)
                _require_text(row, "activity_type", row_number)
                _require_text(row, "instruction", row_number)
                integer(row["minutes"], "minutes", row_number, 0, optional=True)
                for field in ["human_busy", "parallel_ok", "verified"]:
                    flag(row[field], field, row_number)
                decimal(row["attention_load"], "attention_load", row_number, 0.0, 1.0)
                if clean(row["stage"]).lower() not in STAGES:
                    raise ValueError(f"Invalid stage on CSV row {row_number}: {row['stage']!r}")
                equipment_name = clean(row["equipment_name"])
                known_equipment = {"counter", "burner", "oven"}
                if equipment_name.lower() not in known_equipment and not cur.execute(
                    "SELECT 1 FROM equipment WHERE lower(name)=lower(?)", (equipment_name,)
                ).fetchone():
                    raise ValueError(f"Equipment not found on CSV row {row_number}: {equipment_name}")
                dependency = integer(row["depends_on_sequence"], "depends_on_sequence", row_number, 1, optional=True)
                if dependency is not None and dependency >= sequence:
                    raise ValueError(f"depends_on_sequence must precede sequence on CSV row {row_number}.")
                key = (ingredient_name.lower(), role, state_name.lower(), sequence)
                _reject_duplicates(seen, key, row_number)
                if dependency is not None:
                    dependency_key = (ingredient_name.lower(), role, state_name.lower(), dependency)
                    if dependency_key not in seen:
                        raise ValueError(f"depends_on_sequence does not identify an earlier row on CSV row {row_number}.")
                if cur.execute(
                    "SELECT 1 FROM ko_activities WHERE lower(component_name)=lower(?) AND role=? AND lower(state_name)=lower(?) AND sequence=?",
                    (component_name, role, state_name, sequence),
                ).fetchone():
                    raise ValueError(f"KO activity already exists on CSV row {row_number}: {key}")

            elif import_type == "Protein Safety Corrections":
                safe = flag(row["alpha_gal_safe"], "alpha_gal_safe", row_number)
                reason = _require_text(row, "reason", row_number)
                verified = flag(row["verified"], "verified", row_number)
                if not verified:
                    raise ValueError(f"Safety correction must be verified on CSV row {row_number}.")
                key = ingredient_name.lower()
                _reject_duplicates(seen, key, row_number)
                protein = cur.execute(
                    "SELECT alpha_gal_safe FROM proteins WHERE ingredient_id=?", (ingredient_id,)
                ).fetchone()
                if not protein:
                    raise ValueError(f"Protein row not found on CSV row {row_number}: {ingredient_name}")
                if int(protein[0] or 0) == safe:
                    raise ValueError(f"Safety value is already {safe} on CSV row {row_number}: {ingredient_name}")
                if not reason:
                    raise ValueError(f"Blank correction reason on CSV row {row_number}.")
        return rows, []
    finally:
        con.close()


def import_training_rows(rows, import_type, db_path):
    """Import a previously validated wave in one atomic transaction."""
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    imported = 0
    skipped = 0
    try:
        cur = con.cursor()
        for row in rows:
            ingredient_name = clean(row["ingredient_name"])
            ingredient_id = None
            component_name = ingredient_name
            if import_type in {"KO Profiles", "KO Activities"}:
                role = clean(row["role"]).lower()
                ingredient_id, component_name = _component(cur, ingredient_name, role, imported + 2)
            else:
                ingredient_id = _ingredient_id(cur, ingredient_name, imported + 2)

            if import_type == "Ingredient Forms":
                cur.execute(
                    "INSERT INTO ingredient_forms (ingredient_id, form_name, pantry_style, notes) VALUES (?, ?, ?, ?)",
                    (ingredient_id, clean(row["form_name"]), clean(row["pantry_style"]), clean(row["notes"])),
                )

            elif import_type == "Ingredient States":
                cur.execute(
                    """INSERT INTO ingredient_states
                    (ingredient_id, state_name, storage_location, needs_cooking, ready_to_eat,
                     typical_prep_minutes, typical_cook_minutes, active_minutes, passive_minutes,
                     attention_score, energy_level, rank_penalty, holdability, handling_note,
                     timing_note, cooking_note, verified, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (ingredient_id, clean(row["state_name"]), clean(row["storage_location"]),
                     flag(row["needs_cooking"], "needs_cooking", 0), flag(row["ready_to_eat"], "ready_to_eat", 0),
                     int(row["typical_prep_minutes"]), int(row["typical_cook_minutes"]),
                     int(row["active_minutes"]), int(row["passive_minutes"]), int(row["attention_score"]),
                     clean(row["energy_level"]), int(row["rank_penalty"]), clean(row["holdability"]),
                     clean(row["handling_note"]), clean(row["timing_note"]), clean(row["cooking_note"]),
                     flag(row["verified"], "verified", 0), clean(row["notes"])),
                )

            elif import_type == "KO Profiles":
                fields = PROFILE_COLUMNS[1:]
                values = []
                flag_fields = {"parallel_ok", "start_first", "verified"}
                int_fields = {"prep_minutes", "cook_minutes", "active_minutes", "passive_minutes", "attention_score", "rest_minutes", "work_score", "cleanup_score", "mental_load_score"}
                for field in fields:
                    value = row[field]
                    if field in flag_fields:
                        value = flag(value, field, 0)
                    elif field in int_fields:
                        value = int(value)
                    else:
                        value = clean(value)
                    values.append(value)
                columns = ", ".join(["ingredient_id", "component_name"] + fields)
                placeholders = ", ".join(["?"] * (len(fields) + 2))
                cur.execute(f"INSERT INTO ko_profiles ({columns}) VALUES ({placeholders})", [ingredient_id, component_name] + values)

            elif import_type == "KO Activities":
                cur.execute(
                    """INSERT INTO ko_activities
                    (ingredient_id, component_name, role, state_name, sequence, activity_type, instruction,
                     minutes, human_busy, attention_load, equipment_name, stage, parallel_ok,
                     depends_on_sequence, verified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (ingredient_id, component_name, clean(row["role"]).lower(), clean(row["state_name"]), int(row["sequence"]),
                     clean(row["activity_type"]), clean(row["instruction"]),
                     int(row["minutes"]) if clean(row["minutes"]) else None,
                     flag(row["human_busy"], "human_busy", 0), float(row["attention_load"]),
                     clean(row["equipment_name"]), clean(row["stage"]).lower(),
                     flag(row["parallel_ok"], "parallel_ok", 0),
                     int(row["depends_on_sequence"]) if clean(row["depends_on_sequence"]) else None,
                     flag(row["verified"], "verified", 0)),
                )

            elif import_type == "Protein Safety Corrections":
                old_value = cur.execute(
                    "SELECT alpha_gal_safe FROM proteins WHERE ingredient_id=?", (ingredient_id,)
                ).fetchone()[0]
                new_value = flag(row["alpha_gal_safe"], "alpha_gal_safe", 0)
                cur.execute("UPDATE proteins SET alpha_gal_safe=? WHERE ingredient_id=?", (new_value, ingredient_id))
                cur.execute(
                    """INSERT INTO ckb_change_log
                    (change_type, target_table, target_key, field_name, old_value, new_value, reason, changed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("safety correction", "proteins", ingredient_name, "alpha_gal_safe",
                     str(old_value), str(new_value), clean(row["reason"]), datetime.now().isoformat(timespec="seconds")),
                )
            else:
                raise ValueError(f"Unsupported training import type: {import_type}")
            imported += 1
        con.commit()
        return imported, skipped
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
