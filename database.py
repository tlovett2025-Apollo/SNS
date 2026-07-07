import sqlite3
import pandas as pd
from config import DB_PATH
from schema import create_schema


def get_connection():
    create_schema()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def fetch_df(query, params=None):
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params or [])


def insert_row(table, data):
    columns = list(data.keys())
    placeholders = ", ".join(["?"] * len(columns))
    col_sql = ", ".join(columns)
    values = [data[c] for c in columns]
    sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"
    with get_connection() as conn:
        cur = conn.execute(sql, values)
        conn.commit()
        return cur.lastrowid


def update_row(table, id_col, id_value, data):
    clean = {k: v for k, v in data.items() if k != id_col}
    if not clean:
        return 0
    assignments = ", ".join([f"{col} = ?" for col in clean.keys()])
    values = list(clean.values()) + [id_value]
    sql = f"UPDATE {table} SET {assignments} WHERE {id_col} = ?"
    with get_connection() as conn:
        cur = conn.execute(sql, values)
        conn.commit()
        return cur.rowcount


def delete_row(table, id_col, id_value):
    sql = f"DELETE FROM {table} WHERE {id_col} = ?"
    with get_connection() as conn:
        cur = conn.execute(sql, [id_value])
        conn.commit()
        return cur.rowcount


def fetch_options(table, id_col, label_col, where_sql="", params=None):
    sql = f"SELECT {id_col}, {label_col} FROM {table}"
    if where_sql:
        sql += f" WHERE {where_sql}"
    sql += f" ORDER BY {label_col}"
    df = fetch_df(sql, params or [])
    return [(int(r[id_col]), str(r[label_col])) for _, r in df.iterrows()]


def table_count(table):
    df = fetch_df(f"SELECT COUNT(*) AS count FROM {table}")
    return int(df.iloc[0]["count"])


def row_exists(table, column, value, exclude_id_col=None, exclude_id_value=None):
    sql = f"SELECT 1 FROM {table} WHERE LOWER({column}) = LOWER(?)"
    params = [value]
    if exclude_id_col and exclude_id_value is not None:
        sql += f" AND {exclude_id_col} <> ?"
        params.append(exclude_id_value)
    sql += " LIMIT 1"
    return not fetch_df(sql, params).empty


def ingredient_usage(ingredient_id):
    """Return places where an ingredient is referenced. Used for safe edits/deletes."""
    checks = [
        ("proteins", "protein_id", "ingredient_id"),
        ("vegetables", "vegetable_id", "ingredient_id"),
        ("ingredient_forms", "form_id", "ingredient_id"),
        ("ingredient_states", "state_id", "ingredient_id"),
        ("ingredient_nutrition", "nutrition_id", "ingredient_id"),
        ("user_inventory", "inventory_id", "ingredient_id"),
    ]
    out = []
    for table, id_col, fk_col in checks:
        try:
            df = fetch_df(f"SELECT {id_col} FROM {table} WHERE {fk_col} = ?", [ingredient_id])
            for _, row in df.iterrows():
                out.append({"table": table, "id_col": id_col, "row_id": int(row[id_col])})
        except Exception:
            pass
    return out


def ingredient_is_linked(ingredient_id):
    return len(ingredient_usage(ingredient_id)) > 0


def usage_text(usages):
    if not usages:
        return "No references found."
    return "; ".join([f"{u['table']} row {u['row_id']}" for u in usages])


def safe_delete(table, id_col, id_value):
    """Delete with friendly error details. For ingredients, explain references first."""
    if table == "ingredients":
        usages = ingredient_usage(id_value)
        if usages:
            return {
                "ok": False,
                "message": "Cannot delete this ingredient because it is used by: " + usage_text(usages) + ". Mark it inactive or remove those component links first."
            }
    try:
        count = delete_row(table, id_col, id_value)
        return {"ok": True, "message": f"Deleted {count} row(s)."}
    except sqlite3.IntegrityError as e:
        return {"ok": False, "message": f"Cannot delete because another table uses this row. Safer option: mark inactive if available. Details: {e}"}
    except Exception as e:
        return {"ok": False, "message": f"Could not delete: {e}"}
