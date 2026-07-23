"""Canonical form, quantity, and unit contracts for household inventory.

The browser, capture services, recipe engine, and persistence boundary must
interpret an inventory lot the same way.  This module derives practical
inventory choices from verified KO families instead of maintaining a short
second catalog in JavaScript.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
import sqlite3

from config import DB_PATH
from ko_behavior import default_form_for, resolve_behavior


CONTRACT_VERSION = "inventory-2.0"

UNIT_ALIASES = {
    "items": "item", "cans": "can", "jars": "jar", "boxes": "box",
    "bags": "bag", "packages": "package", "pieces": "piece",
    "pounds": "lb", "pound": "lb", "lbs": "lb", "ounces": "oz",
    "ounce": "oz", "cups": "cup", "cartons": "carton",
    "bottles": "bottle", "bunches": "bunch", "loaves": "loaf",
    "slices": "slice", "eggs": "egg", "dozens": "dozen",
    "portions": "portion", "meals": "meal",
}

COUNT_UNITS = {
    "item", "can", "jar", "box", "bag", "package", "piece", "carton",
    "bottle", "bunch", "loaf", "slice", "egg", "dozen", "portion", "meal",
}
MEASURE_UNITS = {"lb", "oz", "cup"}
KNOWN_UNITS = COUNT_UNITS | MEASURE_UNITS

FORM_LABELS = {
    "fresh": "Fresh",
    "fresh raw": "Fresh Raw",
    "frozen": "Frozen",
    "frozen raw": "Frozen Raw",
    "canned": "Canned",
    "cooked": "Cooked",
    "ready to eat": "Ready to Eat",
    "refrigerated": "Refrigerated",
    "dry": "Dry",
    "dried": "Dry",
    "shelf stable": "Shelf-stable",
    "thin sliced raw": "Thin-sliced Raw",
}

# Inventory forms can be more precise than a cooking method's broad eligibility
# form. Preserve the precise form in the saved lot while validating it through
# the compatible method form. This lets planners distinguish a half-inch
# chicken-breast slice from a whole breast without duplicating the ingredient.
FORM_METHOD_EQUIVALENTS = {
    "thin sliced raw": ("fresh raw",),
}

FAMILY_UNIT_RULES = {
    "ground_meat": ("lb", "oz", "package"),
    "tough_meat": ("lb", "oz", "package"),
    "stew_cut": ("lb", "oz", "package"),
    "egg": ("egg", "dozen", "carton"),
    "ready_protein": ("can", "package", "cup", "oz"),
    "prepared_legume": ("can", "jar", "cup", "package"),
    "legume": ("can", "bag", "package", "lb", "cup"),
    "bread_wrap": ("loaf", "slice", "package", "piece"),
    "pasta": ("box", "package", "bag", "lb", "oz", "cup"),
    "white_rice": ("bag", "box", "package", "lb", "cup"),
    "brown_rice": ("bag", "box", "package", "lb", "cup"),
    "quinoa": ("bag", "box", "package", "lb", "cup"),
    "broth_liquid": ("carton", "can", "cup", "bottle"),
    "milk_cream": ("carton", "bottle", "can", "package", "cup"),
    "tomato_product": ("can", "jar", "cup", "package"),
    "creamy_soup_base": ("can", "cup", "package"),
    "prepared_condiment": ("bottle", "jar", "package", "cup"),
    "acid_condiment": ("bottle", "jar", "cup"),
    "cooking_fat": ("bottle", "jar", "package", "lb", "oz", "cup"),
    "melting_cheese": ("package", "lb", "oz", "cup"),
    "cultured_creamy": ("carton", "package", "cup", "oz"),
    "dry_seasoning": ("jar", "bottle", "package", "oz"),
    "salt_seasoning": ("box", "jar", "package", "oz"),
    "dry_baking_helper": ("bag", "box", "package", "lb", "oz", "cup"),
    "sweetener": ("bag", "box", "jar", "bottle", "package", "lb", "oz", "cup"),
    "fresh_herb": ("bunch", "package", "bag", "oz"),
    "aromatic_fast": ("piece", "jar", "package", "bag", "lb", "oz", "cup"),
    "raw_finish": ("piece", "jar", "package", "bag", "lb", "cup", "bunch"),
    "ready_cured_meat": ("package", "piece", "lb", "oz"),
    "bacon": ("package", "piece", "lb", "oz"),
}


class InventoryContractError(ValueError):
    """An inventory lot contradicts its canonical ingredient contract."""


def _clean(value) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value) -> str:
    return _clean(value).lower().replace("-", " ")


def normalize_unit(value) -> str:
    key = _key(value)
    return UNIT_ALIASES.get(key, key)


def quantity_step(unit: str) -> float:
    unit = normalize_unit(unit)
    if unit in {"lb", "cup", "oz", "package"}:
        return 0.25
    if unit == "can":
        return 0.5
    return 1.0


def _storage_for_form(form: str, default_storage: str = "") -> str:
    key = _key(form)
    if "frozen" in key:
        return "Freezer"
    if key in {"canned", "dry", "dried", "shelf stable"}:
        return "Pantry"
    if key in {"refrigerated", "cooked", "ready to eat"}:
        return "Fridge"
    if key in {"fresh", "fresh raw"}:
        return "Fresh" if _key(default_storage) == "fresh" else "Fridge" if _key(default_storage) == "fridge" else "Fresh"
    return FORM_LABELS.get(_key(default_storage), _clean(default_storage)) or "Pantry"


def _role_for(con: sqlite3.Connection, ingredient_id: int, name: str, category: str) -> str:
    if con.execute(
        "SELECT 1 FROM proteins WHERE ingredient_id=? AND verified=1", (ingredient_id,)
    ).fetchone():
        return "protein"
    if con.execute(
        "SELECT 1 FROM vegetables WHERE ingredient_id=? AND verified=1", (ingredient_id,)
    ).fetchone() or _key(category) == "fruit":
        return "vegetable"
    if con.execute(
        "SELECT 1 FROM foundations WHERE lower(name)=lower(?) AND verified=1", (name,)
    ).fetchone():
        return "foundation"
    return "ingredient"


def _forms_for(
    ingredient_id: int,
    family,
    con: sqlite3.Connection,
    selected_form: str = "",
    selected_method=None,
) -> tuple[str, ...]:
    values: list[str] = [
        str(row[0]) for row in con.execute(
            "SELECT form_name FROM ingredient_forms WHERE ingredient_id=? ORDER BY form_id",
            (ingredient_id,),
        ) if _clean(row[0])
    ]
    if family:
        for rule in family.methods:
            for value in rule.forms:
                label = FORM_LABELS.get(_key(value), _clean(value).title())
                if label and _key(label) not in {_key(item) for item in values}:
                    values.append(label)
    # Supporting KOs intentionally use form-agnostic cooking methods. Their
    # storage form still matters, but an empty method.forms tuple means "all
    # verified inventory forms," not "this ingredient has no valid form."
    if selected_method and not selected_method.forms and _clean(selected_form):
        label = FORM_LABELS.get(_key(selected_form), _clean(selected_form))
        if _key(label) not in {_key(item) for item in values}:
            values.append(label)
    return tuple(values)


def _canonical_inventory_form(selected_form: str, forms: tuple[str, ...], family) -> str | None:
    selected_key = _key(selected_form)
    method_keys = {
        _key(value)
        for rule in (family.methods if family else ())
        for value in rule.forms
        if _clean(value)
    }
    by_key = {_key(value): value for value in forms}
    if not method_keys:
        return by_key.get(selected_key) or _clean(selected_form)
    if selected_key in by_key and any(
        method_key in method_keys
        for method_key in FORM_METHOD_EQUIVALENTS.get(selected_key, (selected_key,))
    ):
        return by_key[selected_key]
    aliases = {
        "pantry": ("shelf stable", "dry", "dried", "ready to eat", "cooked"),
        "shelf stable": ("shelf stable", "dry", "dried", "ready to eat", "cooked"),
        "dry": ("dry", "dried", "shelf stable"),
        "dried": ("dried", "dry", "shelf stable"),
        "refrigerated": ("refrigerated", "fresh raw", "cooked", "ready to eat", "fresh"),
        "frozen": ("frozen", "frozen raw"),
        "fresh": ("fresh", "fresh raw"),
        "canned": ("canned", "cooked", "ready to eat"),
    }
    for candidate in aliases.get(selected_key, (selected_key,)):
        if candidate in method_keys:
            return by_key.get(candidate) or FORM_LABELS.get(candidate, candidate.title())
    return None


def _units_for(family_code: str, role: str, form: str, category: str) -> tuple[str, ...]:
    form_key = _key(form)
    if family_code == "raw_fruit" and form_key == "canned":
        units = ["can", "jar", "cup", "package"]
    elif family_code == "raw_fruit" and form_key in {"dry", "dried", "shelf stable"}:
        units = ["bag", "package", "cup", "oz"]
    elif family_code in FAMILY_UNIT_RULES:
        units = list(FAMILY_UNIT_RULES[family_code])
    elif role == "protein":
        units = ["piece", "lb", "oz", "package"]
    elif role == "vegetable":
        units = ["piece", "lb", "bag", "package", "cup", "bunch"]
    elif role == "foundation":
        units = ["package", "bag", "box", "lb", "cup", "piece"]
    elif _key(category) == "spices":
        units = ["jar", "bottle", "package", "oz"]
    else:
        units = ["package", "jar", "bottle", "box", "bag", "lb", "oz", "cup"]
    if form_key == "canned":
        units.insert(0, "can")
    return tuple(dict.fromkeys(unit for unit in units if unit in KNOWN_UNITS))


def _default_unit(family_code: str, form: str, allowed: tuple[str, ...]) -> str:
    if _key(form) == "canned" and "can" in allowed:
        return "can"
    preferred = {
        "egg": "egg", "bread_wrap": "package", "broth_liquid": "carton",
        "milk_cream": "carton", "prepared_condiment": "bottle",
        "acid_condiment": "bottle", "cooking_fat": "bottle",
        "dry_seasoning": "jar", "fresh_herb": "bunch",
    }.get(family_code)
    if preferred in allowed:
        return preferred
    return allowed[0] if allowed else "package"


@dataclass(frozen=True)
class InventoryProfile:
    ingredient_id: int
    name: str
    category: str
    role: str
    family_code: str
    default_form: str
    allowed_forms: tuple[str, ...]
    default_storage: str
    default_unit: str
    allowed_units: tuple[str, ...]
    quantity_step: float
    contract_version: str = CONTRACT_VERSION

    def as_dict(self) -> dict:
        return asdict(self)


def inventory_profile(
    name: str,
    form: str = "",
    *,
    db_path: str | Path = DB_PATH,
) -> InventoryProfile:
    # sqlite3.Connection's context manager controls the transaction but does
    # not close the handle.  Explicit closing matters on Windows, where a
    # lingering handle prevents temporary databases from being removed.
    with closing(sqlite3.connect(db_path)) as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT ingredient_id,name,category,default_storage FROM ingredients WHERE active=1 AND lower(name)=lower(?)",
            (_clean(name),),
        ).fetchone()
        if not row:
            row = con.execute(
                """SELECT i.ingredient_id,i.name,i.category,i.default_storage
                     FROM ingredient_aliases a JOIN ingredients i USING(ingredient_id)
                    WHERE i.active=1 AND lower(a.alias_name)=lower(?)""",
                (_clean(name),),
            ).fetchone()
        if not row:
            raise InventoryContractError(f"Unknown inventory item: {name}")
        role = _role_for(con, int(row["ingredient_id"]), str(row["name"]), str(row["category"] or ""))
        selected_form = _clean(form) or default_form_for(str(row["name"]), role, db_path)
        behavior = resolve_behavior(str(row["name"]), role, selected_form, db_path=db_path)
        family = behavior.primary_family
        family_code = family.code if family else ""
        forms = _forms_for(
            int(row["ingredient_id"]), family, con, selected_form, behavior.method
        )
        canonical_form = _canonical_inventory_form(selected_form, forms, family)
        if not canonical_form:
            raise InventoryContractError(
                f"{row['name']} does not support the inventory form {selected_form or '(blank)'}"
            )
        units = _units_for(family_code, role, canonical_form, str(row["category"] or ""))
        default_unit = _default_unit(family_code, canonical_form, units)
        return InventoryProfile(
            int(row["ingredient_id"]), str(row["name"]), str(row["category"] or ""),
            role, family_code, canonical_form, forms,
            _storage_for_form(canonical_form, str(row["default_storage"] or "")),
            default_unit, units, quantity_step(default_unit),
        )


def normalize_inventory_lot(
    lot: dict,
    canonical_name: str,
    *,
    db_path: str | Path = DB_PATH,
    strict: bool = True,
) -> tuple[dict, InventoryProfile]:
    profile = inventory_profile(canonical_name, _clean(lot.get("form")), db_path=db_path)
    unit = normalize_unit(lot.get("unit")) or profile.default_unit
    if unit not in profile.allowed_units:
        # Earlier My Kitchen versions stored the undifferentiated unit "item."
        # Migrate those rows to the KO default so an existing shared kitchen is
        # not locked out by the stricter contract introduced here.
        if unit == "item":
            unit = profile.default_unit
        elif strict:
            choices = ", ".join(profile.allowed_units)
            raise InventoryContractError(
                f"{profile.name} cannot be stored as {unit}; choose {choices}."
            )
        else:
            unit = profile.default_unit
    normalized = dict(lot)
    normalized.update({
        "name": profile.name,
        "form": profile.default_form,
        "storage_location": _clean(lot.get("storage_location") or lot.get("storage")) or profile.default_storage,
        "unit": unit,
    })
    return normalized, profile


def quantity_in_basis(
    quantity: float,
    unit: str,
    basis: str,
    *,
    package_weight_oz: float = 0,
) -> float | None:
    """Convert only defensible quantities; unknown package sizes stay unknown."""
    value = max(0.0, float(quantity or 0))
    unit = normalize_unit(unit)
    basis = _key(basis)
    ounces = None
    if unit == "lb":
        ounces = value * 16
    elif unit == "oz":
        ounces = value
    elif unit == "package" and package_weight_oz:
        ounces = value * float(package_weight_oz)

    if basis == "weight_oz":
        return ounces / 16 if ounces is not None else None
    if basis == "pieces":
        if unit in {"item", "piece", "egg", "slice"}:
            return value
        if unit == "dozen":
            return value * 12
        # One standard intact protein portion is modeled as four ounces. This
        # prevents one pound of chicken from being misread as one chicken piece.
        return ounces / 4 if ounces is not None else None
    if basis == "cans":
        return value if unit == "can" else None
    if basis in {"dry_cups", "prepared_cups"}:
        return value if unit == "cup" else None
    if basis == "whole_count":
        return value if unit in {"item", "piece", "bunch"} else None
    return value


def _catalog_version(db_path: str | Path) -> tuple[str, int]:
    path = Path(db_path)
    return str(path), path.stat().st_mtime_ns


@lru_cache(maxsize=4)
def _inventory_catalog(path: str, _mtime_ns: int) -> tuple[dict, ...]:
    with closing(sqlite3.connect(path)) as con:
        names = [row[0] for row in con.execute(
            "SELECT name FROM ingredients WHERE active=1 ORDER BY display_order,name"
        )]
        forms_by_name = {
            name: [row[0] for row in con.execute(
                """SELECT f.form_name
                     FROM ingredient_forms f
                     JOIN ingredients i USING(ingredient_id)
                    WHERE lower(i.name)=lower(?)
                    ORDER BY f.form_id""",
                (name,),
            )]
            for name in names
        }
    profiles = []
    for name in names:
        try:
            profile = inventory_profile(name, db_path=path).as_dict()
            form_profiles = []
            for form in forms_by_name[name]:
                try:
                    form_profiles.append(
                        inventory_profile(name, form, db_path=path).as_dict()
                    )
                except InventoryContractError:
                    continue
            profile["form_profiles"] = form_profiles
            profiles.append(profile)
        except InventoryContractError:
            # Untrained identities stay out of the editable inventory catalog.
            continue
    return tuple(profiles)


def inventory_catalog(db_path: str | Path = DB_PATH) -> list[dict]:
    return [dict(profile) for profile in _inventory_catalog(*_catalog_version(db_path))]
