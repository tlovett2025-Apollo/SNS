"""Persistence and handoff helpers for the Stock & Stir inventory editor."""

from pathlib import Path
import sqlite3
from contextlib import closing


PROTOTYPE_USER = "Local Pantry Prototype"


def ensure_prototype_user(con):
    row = con.execute(
        "SELECT user_id FROM users WHERE display_name=? ORDER BY user_id LIMIT 1",
        (PROTOTYPE_USER,),
    ).fetchone()
    if row:
        return int(row[0])
    cursor = con.execute(
        "INSERT INTO users (display_name, default_servings, leftovers_ok) VALUES (?,4,1)",
        (PROTOTYPE_USER,),
    )
    return int(cursor.lastrowid)


def load_saved_form_ids(db_path):
    if not Path(db_path).exists():
        return set()
    with closing(sqlite3.connect(db_path)) as con:
        row = con.execute(
            "SELECT user_id FROM users WHERE display_name=? ORDER BY user_id LIMIT 1",
            (PROTOTYPE_USER,),
        ).fetchone()
        if not row:
            return set()
        return {
            int(saved[0])
            for saved in con.execute(
                "SELECT form_id FROM user_inventory WHERE user_id=? AND form_id IS NOT NULL",
                (int(row[0]),),
            )
        }


def save_inventory(selected, db_path):
    """Replace only the prototype user's recognized inventory atomically."""
    with closing(sqlite3.connect(db_path)) as con:
        with con:
            user_id = ensure_prototype_user(con)
            con.execute("DELETE FROM user_inventory WHERE user_id=?", (user_id,))
            con.executemany(
                """INSERT INTO user_inventory
                   (user_id, ingredient_id, form_id, storage_location, confidence_level)
                   VALUES (?,?,?,?,?)""",
                [
                    (
                        user_id,
                        int(row["ingredient_id"]),
                        int(row["form_id"]),
                        row["storage"],
                        "user_selected",
                    )
                    for row in selected
                ],
            )
    return len(selected)


def inventory_payload(selected, custom_selected):
    known = [
        {
            "ingredient_id": int(row["ingredient_id"]),
            "form_id": int(row["form_id"]),
            "name": row["name"],
            "form": row["form_name"],
            "storage": row["storage"],
            "ckb_known": True,
        }
        for row in selected
    ]
    custom = [
        {
            "ingredient_id": None,
            "form_id": None,
            "name": item["name"],
            "form": item["form_name"],
            "storage": item["section"],
            "ckb_known": False,
        }
        for item in custom_selected
    ]
    return known + custom
