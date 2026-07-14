import sqlite3
from config import DB_PATH

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    default_storage TEXT,
    dairy_flag INTEGER DEFAULT 0,
    gluten_flag INTEGER DEFAULT 0,
    pork_flag INTEGER DEFAULT 0,
    egg_flag INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    notes TEXT,
    knowledge_status TEXT DEFAULT 'real'
);


CREATE TABLE IF NOT EXISTS ingredient_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL,
    alias_name TEXT NOT NULL UNIQUE,
    alias_type TEXT DEFAULT 'synonym',
    notes TEXT,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
);

CREATE TABLE IF NOT EXISTS ingredient_forms (
    form_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL,
    form_name TEXT NOT NULL,
    pantry_style TEXT,
    notes TEXT,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
);


CREATE TABLE IF NOT EXISTS ingredient_states (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL,
    state_name TEXT NOT NULL,
    storage_location TEXT,
    needs_cooking INTEGER DEFAULT 0,
    ready_to_eat INTEGER DEFAULT 0,
    typical_prep_minutes INTEGER DEFAULT 0,
    typical_cook_minutes INTEGER DEFAULT 0,
    energy_level TEXT,
    rank_penalty INTEGER DEFAULT 0,
    notes TEXT,
    UNIQUE(ingredient_id, state_name),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
);

CREATE TABLE IF NOT EXISTS ingredient_nutrition (
    nutrition_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL UNIQUE,
    calories_per_100g REAL,
    protein_g_per_100g REAL,
    carbs_g_per_100g REAL,
    fat_g_per_100g REAL,
    fiber_g_per_100g REAL,
    sodium_mg_per_100g REAL,
    source TEXT,
    notes TEXT,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
);

CREATE TABLE IF NOT EXISTS prep_forms (
    prep_id INTEGER PRIMARY KEY AUTOINCREMENT,
    prep_name TEXT NOT NULL UNIQUE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS equipment (
    equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    equipment_type TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS techniques (
    technique_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    equipment_id INTEGER,
    active_time_minutes INTEGER,
    passive_time_minutes INTEGER,
    energy_level TEXT,
    instruction_template TEXT,
    notes TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
);

CREATE TABLE IF NOT EXISTS proteins (
    protein_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL UNIQUE,
    default_technique_id INTEGER,
    cost_level TEXT,
    energy_level TEXT,
    animal_source TEXT,
    meat_color TEXT,
    alpha_gal_safe INTEGER DEFAULT 0,
    default_prep TEXT,
    notes TEXT,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id),
    FOREIGN KEY (default_technique_id) REFERENCES techniques(technique_id)
);

CREATE TABLE IF NOT EXISTS vegetables (
    vegetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL UNIQUE,
    common_prep_id INTEGER,
    soft_texture_possible INTEGER DEFAULT 0,
    cooks_fast INTEGER DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id),
    FOREIGN KEY (common_prep_id) REFERENCES prep_forms(prep_id)
);

CREATE TABLE IF NOT EXISTS foundations (
    foundation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    foundation_type TEXT,
    texture TEXT,
    pantry_style TEXT,
    energy_level TEXT,
    good_with_gravy INTEGER DEFAULT 0,
    good_with_sauce INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS sauces (
    sauce_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sauce_family TEXT,
    dairy_status TEXT,
    thickener_type TEXT,
    energy_level TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS cuisines (
    cuisine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    cuisine_family TEXT,
    spice_level TEXT,
    default_sauce_family TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS flavor_systems (
    flavor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    cuisine_hint TEXT,
    spice_level TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS meal_templates (
    template_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    meal_occasion TEXT,
    default_equipment_id INTEGER,
    output_style TEXT,
    notes TEXT,
    FOREIGN KEY (default_equipment_id) REFERENCES equipment(equipment_id)
);

CREATE TABLE IF NOT EXISTS template_slots (
    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    slot_name TEXT NOT NULL,
    required INTEGER DEFAULT 1,
    min_count INTEGER DEFAULT 1,
    max_count INTEGER DEFAULT 1,
    FOREIGN KEY (template_id) REFERENCES meal_templates(template_id)
);

CREATE TABLE IF NOT EXISTS compatibility_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_a_type TEXT NOT NULL,
    component_a_id INTEGER NOT NULL,
    component_b_type TEXT NOT NULL,
    component_b_id INTEGER NOT NULL,
    rating TEXT NOT NULL,
    reason TEXT,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS substitution_rules (
    substitution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_type TEXT NOT NULL,
    original_id INTEGER NOT NULL,
    substitute_type TEXT NOT NULL,
    substitute_id INTEGER NOT NULL,
    quality TEXT NOT NULL,
    adjustment_notes TEXT
);

CREATE TABLE IF NOT EXISTS constraint_rules (
    constraint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    constraint_name TEXT NOT NULL,
    component_type TEXT NOT NULL,
    component_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS signature_recipes (
    recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_name TEXT NOT NULL UNIQUE,
    recipe_family TEXT,
    meal_occasion TEXT,
    meal_shape TEXT,
    cuisine TEXT,
    energy_level TEXT,
    cost_level TEXT,
    active_time_minutes INTEGER,
    passive_time_minutes INTEGER,
    total_time_minutes INTEGER,
    servings_default INTEGER DEFAULT 4,
    why_this_works TEXT,
    storage_reheat_notes TEXT,
    comfort_notes TEXT,
    status TEXT DEFAULT 'Draft'
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    default_servings INTEGER DEFAULT 4,
    leftovers_ok INTEGER DEFAULT 1,
    budget_preference TEXT,
    energy_default TEXT
);

CREATE TABLE IF NOT EXISTS households (
    household_id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_name TEXT NOT NULL,
    created_by_user_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by_user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS household_members (
    household_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (household_id, user_id),
    FOREIGN KEY (household_id) REFERENCES households(household_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS user_inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    household_id INTEGER,
    ingredient_id INTEGER NOT NULL,
    form_id INTEGER,
    prep_id INTEGER,
    quantity REAL,
    quantity_band TEXT,
    unit TEXT,
    storage_location TEXT,
    expiration_date TEXT,
    confidence_level TEXT,
    origin TEXT DEFAULT 'manual',
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (household_id) REFERENCES households(household_id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id),
    FOREIGN KEY (form_id) REFERENCES ingredient_forms(form_id),
    FOREIGN KEY (prep_id) REFERENCES prep_forms(prep_id)
);

CREATE TABLE IF NOT EXISTS pending_inventory_items (
    pending_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL,
    submitted_by_user_id INTEGER NOT NULL,
    raw_text TEXT NOT NULL,
    requested_form TEXT,
    storage_location TEXT,
    source_type TEXT NOT NULL DEFAULT 'quick_entry',
    match_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (household_id) REFERENCES households(household_id),
    FOREIGN KEY (submitted_by_user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    preference_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    strength TEXT,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS collections (
    collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_name TEXT NOT NULL UNIQUE,
    collection_type TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS ko_profiles (
    ko_profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER,
    component_name TEXT NOT NULL,
    role TEXT NOT NULL,
    default_state TEXT,
    prep_minutes INTEGER DEFAULT 0,
    cook_minutes INTEGER DEFAULT 0,
    active_minutes INTEGER DEFAULT 0,
    passive_minutes INTEGER DEFAULT 0,
    attention_score INTEGER DEFAULT 0,
    rest_minutes INTEGER DEFAULT 0,
    add_stage TEXT DEFAULT 'middle',
    holdability TEXT,
    preferred_method TEXT,
    desired_outcome TEXT,
    failure_mode TEXT,
    recovery_hint TEXT,
    teaching_note TEXT,
    parallel_ok INTEGER DEFAULT 1,
    start_first INTEGER DEFAULT 0,
    timing_note TEXT,
    handling_note TEXT,
    cooking_note TEXT,
    work_score INTEGER DEFAULT 0,
    cleanup_score INTEGER DEFAULT 0,
    mental_load_score INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0,
    UNIQUE(component_name, role),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
);

CREATE TABLE IF NOT EXISTS ko_activities (
    ko_activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER,
    component_name TEXT NOT NULL,
    role TEXT NOT NULL,
    state_name TEXT NOT NULL DEFAULT '',
    sequence INTEGER NOT NULL,
    activity_type TEXT NOT NULL,
    instruction TEXT NOT NULL,
    minutes INTEGER,
    human_busy INTEGER DEFAULT 1,
    attention_load REAL DEFAULT 1.0,
    equipment_name TEXT,
    stage TEXT DEFAULT 'middle',
    parallel_ok INTEGER DEFAULT 1,
    depends_on_sequence INTEGER,
    verified INTEGER DEFAULT 0,
    UNIQUE(component_name, role, state_name, sequence),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
);

CREATE TABLE IF NOT EXISTS ckb_change_log (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    change_type TEXT NOT NULL,
    target_table TEXT NOT NULL,
    target_key TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT NOT NULL,
    changed_at TEXT NOT NULL
);
"""

MIGRATIONS = [
    ("ingredients", "knowledge_status", "ALTER TABLE ingredients ADD COLUMN knowledge_status TEXT DEFAULT 'real'"),
    ("proteins", "animal_source", "ALTER TABLE proteins ADD COLUMN animal_source TEXT"),
    ("proteins", "meat_color", "ALTER TABLE proteins ADD COLUMN meat_color TEXT"),
    ("proteins", "alpha_gal_safe", "ALTER TABLE proteins ADD COLUMN alpha_gal_safe INTEGER DEFAULT 0"),
    ("proteins", "default_prep", "ALTER TABLE proteins ADD COLUMN default_prep TEXT"),
    ("ingredient_states", "active_minutes", "ALTER TABLE ingredient_states ADD COLUMN active_minutes INTEGER DEFAULT 0"),
    ("ingredient_states", "passive_minutes", "ALTER TABLE ingredient_states ADD COLUMN passive_minutes INTEGER DEFAULT 0"),
    ("ingredient_states", "attention_score", "ALTER TABLE ingredient_states ADD COLUMN attention_score INTEGER DEFAULT 0"),
    ("ingredient_states", "holdability", "ALTER TABLE ingredient_states ADD COLUMN holdability TEXT"),
    ("ingredient_states", "handling_note", "ALTER TABLE ingredient_states ADD COLUMN handling_note TEXT"),
    ("ingredient_states", "timing_note", "ALTER TABLE ingredient_states ADD COLUMN timing_note TEXT"),
    ("ingredient_states", "cooking_note", "ALTER TABLE ingredient_states ADD COLUMN cooking_note TEXT"),
    ("ingredient_states", "verified", "ALTER TABLE ingredient_states ADD COLUMN verified INTEGER DEFAULT 0"),
    ("user_inventory", "household_id", "ALTER TABLE user_inventory ADD COLUMN household_id INTEGER"),
    ("user_inventory", "quantity_band", "ALTER TABLE user_inventory ADD COLUMN quantity_band TEXT"),
    ("user_inventory", "origin", "ALTER TABLE user_inventory ADD COLUMN origin TEXT DEFAULT 'manual'"),
]


def _table_exists(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", [table]).fetchone() is not None


def _column_exists(conn, table, column):
    if not _table_exists(conn, table):
        return False
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _run_migrations(conn):
    for table, column, sql in MIGRATIONS:
        if _table_exists(conn, table) and not _column_exists(conn, table, column):
            conn.execute(sql)


def create_schema():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA_SQL)
        _run_migrations(conn)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_inventory_household ON user_inventory(household_id)"
        )
        conn.commit()


if __name__ == "__main__":
    create_schema()
    print(f"Schema created at {DB_PATH}")
