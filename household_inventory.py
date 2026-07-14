"""Canonical household inventory service.

This is the application boundary that a future HTTP API will call.  UI code
does not own inventory rules and recipe code should receive a household_id,
then load the canonical inventory through this module.
"""

from contextlib import closing
from datetime import date
import sqlite3


LOCAL_USER = "Local Pantry Tester"
LOCAL_HOUSEHOLD = "Local Test Kitchen"


class InventoryError(ValueError):
    pass


class InventoryAccessError(PermissionError):
    pass


def ensure_inventory_schema(con):
    con.executescript(
        """
        PRAGMA foreign_keys=ON;
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
            PRIMARY KEY (household_id,user_id),
            FOREIGN KEY (household_id) REFERENCES households(household_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
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
        """
    )
    columns = {row[1] for row in con.execute("PRAGMA table_info(user_inventory)")}
    if "household_id" not in columns:
        con.execute("ALTER TABLE user_inventory ADD COLUMN household_id INTEGER")
    if "quantity_band" not in columns:
        con.execute("ALTER TABLE user_inventory ADD COLUMN quantity_band TEXT")
    if "origin" not in columns:
        con.execute("ALTER TABLE user_inventory ADD COLUMN origin TEXT DEFAULT 'manual'")
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_inventory_household ON user_inventory(household_id)"
    )


def bootstrap_local_household(db_path):
    """Create/reuse an explicit local test identity; never impersonates real users."""
    with closing(sqlite3.connect(db_path)) as con:
        with con:
            ensure_inventory_schema(con)
            user = con.execute(
                "SELECT user_id FROM users WHERE display_name=? ORDER BY user_id LIMIT 1",
                (LOCAL_USER,),
            ).fetchone()
            if user:
                user_id = int(user[0])
            else:
                user_id = int(con.execute(
                    "INSERT INTO users (display_name,default_servings,leftovers_ok) VALUES (?,4,1)",
                    (LOCAL_USER,),
                ).lastrowid)
            household = con.execute(
                "SELECT household_id FROM households WHERE household_name=? AND created_by_user_id=? ORDER BY household_id LIMIT 1",
                (LOCAL_HOUSEHOLD, user_id),
            ).fetchone()
            if household:
                household_id = int(household[0])
            else:
                household_id = int(con.execute(
                    "INSERT INTO households (household_name,created_by_user_id) VALUES (?,?)",
                    (LOCAL_HOUSEHOLD, user_id),
                ).lastrowid)
            con.execute(
                "INSERT OR IGNORE INTO household_members (household_id,user_id,role) VALUES (?,?,'owner')",
                (household_id, user_id),
            )
            return user_id, household_id


def _require_member(con, household_id, acting_user_id):
    member = con.execute(
        "SELECT 1 FROM household_members WHERE household_id=? AND user_id=?",
        (household_id, acting_user_id),
    ).fetchone()
    if not member:
        raise InventoryAccessError("User is not a member of this household")


def _validate_item(con, item):
    try:
        ingredient_id = int(item["ingredient_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InventoryError("ingredient_id is required") from exc
    form_id = item.get("form_id")
    form_id = int(form_id) if form_id is not None else None
    quantity = item.get("quantity")
    if quantity is not None:
        quantity = float(quantity)
        if quantity < 0:
            raise InventoryError("quantity cannot be negative")
    quantity_band = item.get("quantity_band")
    if quantity_band not in (None, "", "a_little", "some", "plenty"):
        raise InventoryError("quantity_band must be a_little, some, or plenty")
    expiration = item.get("expiration_date")
    if expiration:
        try:
            date.fromisoformat(str(expiration))
        except ValueError as exc:
            raise InventoryError("expiration_date must be YYYY-MM-DD") from exc
    if not con.execute("SELECT 1 FROM ingredients WHERE ingredient_id=?", (ingredient_id,)).fetchone():
        raise InventoryError(f"Unknown ingredient_id: {ingredient_id}")
    if form_id is not None and not con.execute(
        "SELECT 1 FROM ingredient_forms WHERE form_id=? AND ingredient_id=?",
        (form_id, ingredient_id),
    ).fetchone():
        raise InventoryError("form_id does not belong to ingredient_id")
    return {
        "ingredient_id": ingredient_id,
        "form_id": form_id,
        "quantity": quantity,
        "quantity_band": quantity_band or None,
        "unit": item.get("unit"),
        "storage_location": item.get("storage_location") or item.get("storage"),
        "expiration_date": expiration or None,
        "confidence_level": item.get("confidence_level") or "user_selected",
        "origin": item.get("origin") or "manual",
    }


def replace_household_inventory(db_path, household_id, acting_user_id, items):
    """Atomically replace a household inventory after validating every row."""
    with closing(sqlite3.connect(db_path)) as con:
        with con:
            ensure_inventory_schema(con)
            _require_member(con, household_id, acting_user_id)
            validated = [_validate_item(con, item) for item in items]
            con.execute("DELETE FROM user_inventory WHERE household_id=?", (household_id,))
            con.executemany(
                """INSERT INTO user_inventory
                   (household_id,user_id,ingredient_id,form_id,quantity,unit,
                    storage_location,expiration_date,confidence_level,quantity_band,origin)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                [(
                    household_id, acting_user_id, item["ingredient_id"], item["form_id"],
                    item["quantity"], item["unit"], item["storage_location"],
                    item["expiration_date"], item["confidence_level"],
                    item["quantity_band"], item["origin"],
                ) for item in validated],
            )
            return len(validated)


def get_household_inventory(db_path, household_id, acting_user_id):
    with closing(sqlite3.connect(db_path)) as con:
        con.row_factory = sqlite3.Row
        ensure_inventory_schema(con)
        _require_member(con, household_id, acting_user_id)
        return [dict(row) for row in con.execute(
            """SELECT ui.inventory_id,ui.household_id,ui.ingredient_id,ui.form_id,
                      i.name, f.form_name, ui.quantity,ui.unit,ui.storage_location,
                      ui.expiration_date,ui.confidence_level,ui.quantity_band,ui.origin
               FROM user_inventory ui
               JOIN ingredients i ON i.ingredient_id=ui.ingredient_id
               LEFT JOIN ingredient_forms f ON f.form_id=ui.form_id
               WHERE ui.household_id=? ORDER BY i.name,f.form_name""",
            (household_id,),
        )]


def submit_pending_items(db_path, household_id, acting_user_id, items, source_type="quick_entry"):
    """Store unmatched text for later matching/confirmation; never edits the CKB."""
    with closing(sqlite3.connect(db_path)) as con:
        with con:
            ensure_inventory_schema(con)
            _require_member(con, household_id, acting_user_id)
            clean_items = [item for item in items if str(item.get("name") or "").strip()]
            inserted = 0
            for item in clean_items:
                values = (
                    household_id, acting_user_id, str(item["name"]).strip(),
                    item.get("form_name"), item.get("section"), source_type,
                )
                duplicate = con.execute(
                    """SELECT 1 FROM pending_inventory_items
                       WHERE household_id=? AND submitted_by_user_id=?
                         AND lower(raw_text)=lower(?)
                         AND COALESCE(requested_form,'')=COALESCE(?,'')
                         AND COALESCE(storage_location,'')=COALESCE(?,'')
                         AND source_type=? AND match_status='pending'""",
                    values,
                ).fetchone()
                if not duplicate:
                    con.execute(
                        """INSERT INTO pending_inventory_items
                           (household_id,submitted_by_user_id,raw_text,requested_form,storage_location,source_type)
                           VALUES (?,?,?,?,?,?)""",
                        values,
                    )
                    inserted += 1
            return inserted
