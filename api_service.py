"""Application service boundary for the public Stock & Stir website.

This module intentionally contains no HTTP framework and no browser/session
authentication.  A hosted API can call these functions after it has resolved
the authenticated household and acting user.  Keeping that boundary explicit
prevents the static-site prototype from becoming production authentication.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from datetime import date

from config import DB_PATH
from build_provenance import DEPLOYED_BUILD_PROVENANCE, public_build_provenance
from household_inventory import replace_household_inventory, submit_pending_items
from inventory_contract import InventoryContractError, normalize_inventory_lot
from ko_behavior import default_form_for, resolve_behavior
from meal_components import suggest_known_sides
from recipe_engine import build_recipe_from_candidate, generate_candidates


CONTRACT_VERSION = "1.0"

_BROAD_INGREDIENT_DEFAULTS = {}

_MEAL_SHAPES = {
    "quick_bowl": "bowl",
    "skillet": "plate",
    "casserole": "casserole",
    "soup": "soup",
    "plate": "plate",
    "handheld": "sandwich",
    "kid_adventure": "plate",
    "cold_meal": "plate",
    "grill": "plate",
    "braise": "plate",
    "oven_braise": "plate",
}

_LIVE_PLANNER_METHODS = {
    "skillet", "casserole", "soup", "handheld", "grill", "braise", "oven_braise"
}

_BUILDER_METHODS = (
    {"id": "skillet", "label": "Stovetop", "description": "One or more stovetop vessels; meal structure decides whether components join or stay separate."},
    {"id": "soup", "label": "Soup or Stew", "description": "A liquid-led one-vessel meal; SNS chooses the suitable owned pot."},
    {"id": "casserole", "label": "Oven Bake", "description": "An oven-baked meal assembled in one baking dish."},
    {"id": "handheld", "label": "Handheld", "description": "Components cooked as needed, then assembled with bread or a wrap."},
    {"id": "grill", "label": "Grill", "description": "Direct and indirect grill zones with ingredient-specific doneness, flare-up, basket, and resting guidance."},
)

_BUILDER_EXTRA_NAMES = (
    "Mayonnaise", "Salsa", "Ketchup", "Mustard", "BBQ sauce", "Hot sauce",
    "Soy sauce", "Worcestershire sauce", "Pickles", "Sour cream",
    "Greek yogurt", "Cream cheese", "Cheddar cheese", "Mozzarella cheese",
    "Parmesan cheese", "Chicken broth", "Beef broth", "Vegetable broth",
    "Tomato sauce", "Tomato paste", "Diced tomatoes", "Rotel",
    "Cream of mushroom soup", "Cream of chicken soup", "Coconut milk",
    "Peanut butter", "Butter", "Olive oil", "Sesame oil",
)
_BUILDER_EXTRA_ALIASES = {
    "mayo": "Mayonnaise",
    "corn starch": "Cornstarch",
    "cooking oil": "Vegetable oil",
    "ribeye": "Ribeye steak",
    "rib eye": "Ribeye steak",
}

_PROTEIN_CATEGORIES = {
    "beans", "beef", "chicken", "eggs", "plant protein", "pork", "processed meat",
    "protein", "seafood", "turkey",
}

_EXCLUSION_GROUPS = {
    "shellfish": {
        "shrimp", "prawns", "crab", "lobster", "crawfish", "crayfish",
        "clams", "mussels", "oysters", "scallops",
    },
    "shell fish": {
        "shrimp", "prawns", "crab", "lobster", "crawfish", "crayfish",
        "clams", "mussels", "oysters", "scallops",
    },
    "crustaceans": {"shrimp", "prawns", "crab", "lobster", "crawfish", "crayfish"},
    "mollusks": {"clams", "mussels", "oysters", "scallops"},
    "peanuts": {"peanuts", "peanut", "peanut butter"},
    "pork": {
        "pork", "bacon", "ham", "prosciutto", "pancetta", "pork sausage",
    },
}


def _expand_exclusions(values) -> list[str]:
    """Expand household safety categories before any candidate is generated."""
    expanded = []
    for value in values or []:
        name = _clean(value.get("name")) if isinstance(value, dict) else _clean(value)
        if not name:
            continue
        for item in (name, *_EXCLUSION_GROUPS.get(_key(name), set())):
            if _key(item) not in {_key(existing) for existing in expanded}:
                expanded.append(item)
    return expanded


class APIContractError(ValueError):
    """Raised when a request cannot satisfy the public API contract."""


@dataclass(frozen=True)
class ResolvedIngredient:
    ingredient_id: int
    name: str
    category: str
    form_id: int | None
    form_name: str | None
    source: dict


def _clean(value) -> str:
    return "" if value is None else str(value).strip()


def _key(value) -> str:
    return " ".join(_clean(value).lower().replace("-", " ").split())


def _inventory_from(payload: dict) -> list[dict]:
    if not isinstance(payload, dict):
        raise APIContractError("Request body must be a JSON object")
    inventory = payload.get("inventory_lots", payload.get("inventory", []))
    if not isinstance(inventory, list):
        raise APIContractError("inventory must be a list")
    return [item for item in inventory if isinstance(item, dict) and _clean(item.get("name"))]


def _builder_extra_names(db_path: str | Path = DB_PATH) -> tuple[str, ...]:
    """Expose every trained seasoning plus the curated pantry/fridge helpers."""
    with closing(sqlite3.connect(db_path)) as con:
        pantry_rows = con.execute(
            """SELECT name FROM ingredients
               WHERE active=1 AND (
                   lower(category)='spices'
                   OR lower(name) IN ('salt','cornstarch','canola oil','vegetable oil')
               )
               ORDER BY name"""
        ).fetchall()
    return tuple(dict.fromkeys([*_BUILDER_EXTRA_NAMES, *(row[0] for row in pantry_rows)]))


def _quantity_band(item: dict) -> str | None:
    raw = item.get("quantity_band", item.get("amount"))
    if raw in (None, "", 0, "0", "none"):
        return None
    aliases = {
        1: "a_little",
        "1": "a_little",
        "little": "a_little",
        "a little": "a_little",
        "a_little": "a_little",
        2: "some",
        "2": "some",
        "some": "some",
        3: "plenty",
        "3": "plenty",
        "plenty": "plenty",
    }
    band = aliases.get(raw, aliases.get(_key(raw)))
    if not band:
        raise APIContractError(f"Unknown quantity band: {raw}")
    return band


def normalize_kitchen_snapshot(payload: dict) -> dict:
    """Return the canonical, additive v1 representation of a kitchen request."""
    inventory = []
    for item in _inventory_from(payload):
        raw_name = _clean(item.get("name"))
        canonical_name = _BUILDER_EXTRA_ALIASES.get(_key(raw_name), raw_name)
        band = _quantity_band(item)
        quantity = item.get("quantity")
        if quantity not in (None, ""):
            try:
                quantity = float(quantity)
            except (TypeError, ValueError) as exc:
                raise APIContractError("quantity must be a number") from exc
            if quantity < 0:
                raise APIContractError("quantity cannot be negative")
        else:
            quantity = None
        if not band and not quantity:
            continue
        inventory.append({
            "inventory_lot_id": item.get("inventory_lot_id"),
            "ingredient_id": item.get("ingredient_id"),
            "name": canonical_name,
            "form": _clean(item.get("form")) or None,
            "storage_location": _clean(
                item.get("storage_location", item.get("storage"))
            ) or None,
            "quantity": quantity,
            "unit": _clean(item.get("unit")) or None,
            "quantity_band": band,
            "origin": _clean(item.get("origin")) or "manual",
            "opened_at": _clean(item.get("opened_at")) or None,
            "refrigerated_after_opening": item.get("refrigerated_after_opening"),
            "package_weight_oz": item.get("package_weight_oz"),
            "expiration_date": _clean(item.get("expiration_date")) or None,
        })
    return {
        "api_version": CONTRACT_VERSION,
        "household_id": payload.get("household_id"),
        "generated_at": payload.get("generated_at"),
        "inventory_lots": inventory,
        "equipment": list(payload.get("equipment") or []),
        "meal_preferences": dict(payload.get("meal_preferences") or {}),
        "cost_filter": payload.get("cost_filter"),
    }


def _ingredient_row(con: sqlite3.Connection, name: str):
    requested = _BROAD_INGREDIENT_DEFAULTS.get(_key(name), name)
    row = con.execute(
        """SELECT i.ingredient_id,i.name,i.category
             FROM ingredients i
            WHERE lower(i.name)=lower(?)
            LIMIT 1""",
        (requested,),
    ).fetchone()
    if row:
        return row
    return con.execute(
        """SELECT i.ingredient_id,i.name,i.category
             FROM ingredient_aliases a
             JOIN ingredients i ON i.ingredient_id=a.ingredient_id
            WHERE lower(a.alias_name)=lower(?)
            LIMIT 1""",
        (requested,),
    ).fetchone()


def _form_row(con: sqlite3.Connection, ingredient_id: int, form_name: str | None):
    if not form_name:
        return None
    return con.execute(
        """SELECT form_id,form_name FROM ingredient_forms
            WHERE ingredient_id=? AND lower(form_name)=lower(?) LIMIT 1""",
        (ingredient_id, form_name),
    ).fetchone()


def resolve_inventory(
    payload: dict,
    db_path: str | Path = DB_PATH,
    *,
    strict_contract: bool = False,
) -> tuple[list[ResolvedIngredient], list[dict]]:
    """Resolve household names to CKB identities without editing the CKB."""
    snapshot = normalize_kitchen_snapshot(payload)
    resolved: list[ResolvedIngredient] = []
    pending: list[dict] = []
    with closing(sqlite3.connect(db_path)) as con:
        con.row_factory = sqlite3.Row
        for item in snapshot["inventory_lots"]:
            row = _ingredient_row(con, item["name"])
            if not row:
                pending.append({
                    "name": item["name"],
                    "form_name": item["form"],
                    "section": item["storage_location"],
                })
                continue
            try:
                normalized_item, _profile = normalize_inventory_lot(
                    item, str(row["name"]), db_path=db_path, strict=strict_contract
                )
                normalized_item["_requested_name"] = item["name"]
            except InventoryContractError as exc:
                raise APIContractError(str(exc)) from exc
            except sqlite3.OperationalError:
                # Tiny legacy/test databases can predate the KO contract
                # tables. Their existing local persistence path remains
                # usable; production's complete CKB always takes the strict
                # branch above.
                normalized_item = dict(item)
            form = _form_row(
                con, int(row["ingredient_id"]), normalized_item["form"]
            )
            resolved.append(ResolvedIngredient(
                ingredient_id=int(row["ingredient_id"]),
                name=str(row["name"]),
                category=str(row["category"]),
                form_id=int(form["form_id"]) if form else None,
                form_name=(
                    str(form["form_name"])
                    if form else normalized_item["form"]
                ),
                source=normalized_item,
            ))
    return resolved, pending


def get_meal_builder_options(payload: dict | None = None, db_path: str | Path = DB_PATH) -> dict:
    """Return the trained choice catalog with current-kitchen ownership flags."""
    kitchen = payload if isinstance(payload, dict) else {}
    resolved, _pending = resolve_inventory(kitchen, db_path)
    resolved_by_name = {_key(item.name): item for item in resolved}
    owned = {_key(item.name) for item in resolved}
    for item in _inventory_from(kitchen):
        raw_key = _key(item.get("name"))
        owned.add(_key(_BUILDER_EXTRA_ALIASES.get(raw_key, item.get("name"))))
    with closing(sqlite3.connect(db_path)) as con:
        con.row_factory = sqlite3.Row
        proteins = con.execute(
            """SELECT i.name FROM proteins p JOIN ingredients i USING (ingredient_id)
               WHERE i.active=1 AND p.verified=1 ORDER BY i.display_order,i.name"""
        ).fetchall()
        produce = con.execute(
            """SELECT i.name,'vegetable' AS kind FROM vegetables v
                 JOIN ingredients i USING (ingredient_id)
               WHERE i.active=1 AND v.verified=1
               UNION ALL
               SELECT i.name,'fruit' AS kind FROM ingredients i
               WHERE i.active=1 AND lower(i.category)='fruit'
               ORDER BY kind,name"""
        ).fetchall()
        foundations = con.execute(
            """SELECT name FROM foundations WHERE verified=1 ORDER BY foundation_id"""
        ).fetchall()
        cuisines = con.execute("SELECT name FROM cuisines ORDER BY cuisine_id").fetchall()
        ingredient_metadata = {
            _key(row["name"]): {
                "category": row["category"],
                "canned": bool(row["has_canned_form"]),
            }
            for row in con.execute(
                """SELECT i.name,i.category,
                          MAX(CASE WHEN lower(f.form_name) LIKE '%canned%' THEN 1 ELSE 0 END) AS has_canned_form
                   FROM ingredients i LEFT JOIN ingredient_forms f USING (ingredient_id)
                   WHERE i.active=1 GROUP BY i.ingredient_id,i.name,i.category"""
            ).fetchall()
        }

    def choice(name: str, **extra) -> dict:
        inventory_item = resolved_by_name.get(_key(name))
        metadata = ingredient_metadata.get(_key(name), {})
        return {
            "name": name,
            "owned": _key(name) in owned,
            "form": inventory_item.form_name if inventory_item else None,
            "category": metadata.get("category", ""),
            "canned": bool(
                metadata.get("canned")
                or "canned" in _key(inventory_item.form_name if inventory_item else "")
            ),
            **extra,
        }

    def protein_choice(name: str) -> dict:
        item = choice(name)
        form = item.get("form") or ""
        behavior = resolve_behavior(name, "protein", form, db_path=db_path)
        family = behavior.primary_family
        functions = set(family.culinary_functions) if family else set()
        relationships = set(family.relationship_traits) if family else set()
        physical = set(family.physical_traits) if family else set()
        item["default_state"] = (
            "Canned" if "canned" in _key(form)
            else "Cooked" if physical & {"ready-to-eat", "cooked"}
            else "Frozen Raw" if "frozen" in _key(form)
            else "Fresh Raw"
        )
        item["suggested_role"] = (
            "stretch" if "protein-stretcher" in functions
            else "accent" if "accent-capable" in relationships
            else "supporting"
        )
        item["family_code"] = family.code if family else ""
        return item

    equipment_values = kitchen.get("equipment") or []
    equipment_names = [
        _clean(item.get("display_name", item.get("name"))) if isinstance(item, dict) else _clean(item)
        for item in equipment_values
    ]
    owns_grill = any("grill" in _key(name) for name in equipment_names)
    methods = [
        {**item, "available": item["id"] != "grill" or owns_grill,
         **({"note": "Add a grill in My Kitchen to plan this environment."} if item["id"] == "grill" and not owns_grill else {})}
        for item in _BUILDER_METHODS
    ]

    return {
        "api_version": CONTRACT_VERSION,
        "proteins": [protein_choice(row["name"]) for row in proteins],
        "produce": [choice(row["name"], kind=row["kind"]) for row in produce],
        "foundations": [choice(row["name"]) for row in foundations],
        "extras": [choice(name) for name in _builder_extra_names(db_path)],
        "cuisines": [row["name"] for row in cuisines],
        "methods": methods,
        "meal_structures": [
            {"id": "integrated", "label": "Cooked Together", "description": "A cohesive one-vessel meal whose compatible ingredients join in stages."},
            {"id": "composed_plate", "label": "Composed Plate", "description": "Protein, vegetables, and a selected side prepared independently."},
            {"id": "layered_bowl", "label": "Layered Bowl", "description": "A side or base with the other components arranged or spooned over it."},
        ],
        "serving_temperatures": [
            {"id": "hot", "label": "Hot", "available": True},
            {"id": "cold", "label": "Cold", "available": False,
             "note": "Cold meal planning is the next cooking grammar being trained."},
        ],
        "meal_occasions": ["Breakfast", "Lunch", "Dinner", "Any"],
    }


def get_known_side_suggestions(payload: dict, db_path: str | Path = DB_PATH) -> dict:
    """Suggest executable side archetypes after the user chooses a main."""
    if not isinstance(payload, dict):
        raise APIContractError("A kitchen and selected protein are required.")
    kitchen = payload.get("kitchen") if isinstance(payload.get("kitchen"), dict) else payload
    selections = payload.get("selections") if isinstance(payload.get("selections"), dict) else {}
    proteins = selections.get("proteins") or []
    first = proteins[0] if proteins else selections.get("protein")
    protein = _clean(first.get("name")) if isinstance(first, dict) else _clean(first)
    if not protein:
        return {"api_version": CONTRACT_VERSION, "for_protein": "", "suggestions": []}

    _snapshot, _resolved, _pending, engine_request = _engine_request(kitchen, db_path)
    excluded = {_key(item) for item in engine_request.get("excluded_items") or []}
    if _key(protein) in excluded:
        raise APIContractError(f"{protein} is blocked by the household food-safety settings.")
    options = get_meal_builder_options(kitchen, db_path)
    foundation_names = [
        item["name"] for item in options["foundations"] if _key(item["name"]) not in excluded
    ]
    produce_names = [
        item["name"] for item in options["produce"]
        if item.get("kind") == "vegetable" and _key(item["name"]) not in excluded
    ]
    inventory_names = [
        item for item in engine_request.get("available_items") or [] if _key(item) not in excluded
    ]
    suggestions = suggest_known_sides(
        inventory_names, foundation_names, produce_names,
        protein=protein,
        equipment_names=engine_request.get("available_equipment") or [],
    )
    return {
        "api_version": CONTRACT_VERSION,
        "for_protein": protein,
        "suggestions": suggestions,
    }


def save_my_kitchen(
    payload: dict,
    *,
    household_id: int,
    acting_user_id: int,
    db_path: str | Path = DB_PATH,
) -> dict:
    """Persist a kitchen after a trusted HTTP/auth layer resolves membership."""
    resolved, pending = resolve_inventory(payload, db_path, strict_contract=True)
    items = [{
        "ingredient_id": item.ingredient_id,
        "form_id": item.form_id,
        "quantity": item.source.get("quantity"),
        "unit": item.source.get("unit"),
        "storage_location": item.source.get("storage_location"),
        "quantity_band": item.source.get("quantity_band"),
        "origin": item.source.get("origin") or "manual",
        "opened_at": item.source.get("opened_at"),
        "refrigerated_after_opening": item.source.get("refrigerated_after_opening"),
        "package_weight_oz": item.source.get("package_weight_oz"),
        "expiration_date": item.source.get("expiration_date"),
    } for item in resolved]
    saved = replace_household_inventory(
        db_path, household_id, acting_user_id, items
    )
    pending_count = submit_pending_items(
        db_path, household_id, acting_user_id, pending, source_type="public_site"
    ) if pending else 0
    return {
        "api_version": CONTRACT_VERSION,
        "household_id": household_id,
        "saved_inventory_lots": saved,
        "pending_items": pending_count,
    }


def _protein_state(item: ResolvedIngredient | None) -> str:
    form = _key(item.form_name if item else "")
    name = _key(item.name if item else "")
    if "canned" in form or name.startswith("canned "):
        return "Canned"
    if "frozen" in form:
        return "Frozen Raw"
    if any(word in form for word in ("cooked", "prepared", "leftover", "ready to eat")) or "rotisserie" in name:
        return "Cooked"
    return "Fresh Raw"


def _engine_request(payload: dict, db_path: str | Path):
    snapshot = normalize_kitchen_snapshot(payload)
    resolved, pending = resolve_inventory(snapshot, db_path)
    unique_resolved = []
    seen_resolved = set()
    for item in resolved:
        key = (_key(item.name), _key(item.form_name))
        if key in seen_resolved:
            continue
        seen_resolved.add(key)
        unique_resolved.append(item)
    resolved = unique_resolved
    protein = next(
        (item for item in resolved if _key(item.category) in _PROTEIN_CATEGORIES),
        None,
    )
    vegetables = [item for item in resolved if _key(item.category) == "vegetables"]
    foundations = []
    with closing(sqlite3.connect(db_path)) as con:
        for item in resolved:
            if con.execute(
                "SELECT 1 FROM foundations WHERE lower(name)=lower(?) LIMIT 1",
                (item.name,),
            ).fetchone():
                foundations.append(item)

    preferences = snapshot["meal_preferences"]
    excluded_items = []
    for field in ("excluded_items", "exclusions", "ingredient_exclusions"):
        values = preferences.get(field) or []
        if isinstance(values, str):
            values = [values]
        for value in values:
            name = _clean(value.get("name")) if isinstance(value, dict) else _clean(value)
            if name and name not in excluded_items:
                excluded_items.append(name)
    excluded_items = _expand_exclusions(excluded_items)
    names = [item.name for item in resolved]
    equipment = [
        _clean(item.get("display_name", item.get("name"))) if isinstance(item, dict) else _clean(item)
        for item in snapshot["equipment"]
    ]
    return snapshot, resolved, pending, {
        "protein_name": protein.name if protein else "",
        "vegetable_name": vegetables[0].name if vegetables else "",
        "foundation_name": foundations[0].name if foundations else "",
        "cuisine_name": _clean(payload.get("cuisine")) or "Comfort Food",
        "energy_level": _clean(payload.get("energy")) or "Low",
        # Cost is deliberately neutral inside culinary generation.  It can
        # filter valid candidates once pricing data exists.
        "budget_level": "Moderate",
        "time_minutes": preferences.get("maximum_active_minutes") or payload.get("time_minutes") or 45,
        "servings": payload.get("servings") or 4,
        "max_results": payload.get("max_results") or 10,
        "vegetable_names": [item.name for item in vegetables],
        "protein_state": _protein_state(protein),
        "available_items": names,
        "available_equipment": [name for name in equipment if name],
        "excluded_items": excluded_items,
        "inventory_lots": snapshot["inventory_lots"],
        "foundation_names": [item.name for item in foundations],
        "component_forms": {
            item.name: item.form_name for item in resolved if item.form_name
        },
        "recent_meals": list(preferences.get("recent_meals") or []),
        "effort_level": _clean(payload.get("effort")) or _clean(payload.get("energy")) or "Low",
        "eater_profiles": preferences.get("eater_profiles") or {},
    }


def _match_text(score: int) -> str:
    if score >= 90:
        return "Strong match"
    if score >= 70:
        return "Good match"
    return "Possible match"


def _slug(value: str) -> str:
    return "-".join(part for part in _key(value).split() if part)


def _concept_requests(engine_request: dict, resolved: list[ResolvedIngredient]):
    """Build a bounded but varied pantry concept pool before method planning."""
    proteins = [
        item for item in resolved if _key(item.category) in _PROTEIN_CATEGORIES
    ]
    vegetables = [item for item in resolved if _key(item.category) == "vegetables"]
    foundations = list(engine_request.get("foundation_names") or [])[:2]
    flavor_directions = ["Comfort Food"]
    for item_name in engine_request.get("available_items") or []:
        affinities = resolve_behavior(
            item_name, "ingredient", db_path=DB_PATH
        ).attributes.get("cuisine_affinity", "")
        for cuisine in affinities.split(","):
            cuisine = _clean(cuisine)
            if cuisine and cuisine not in flavor_directions:
                flavor_directions.append(cuisine)
    flavor_directions = flavor_directions[:3]

    if not proteins:
        return [(dict(engine_request), None)]

    concepts = []
    seen = set()
    vegetable_names = [item.name for item in vegetables]
    for protein_index, protein in enumerate(proteins):
        if vegetable_names:
            first = vegetable_names[protein_index % len(vegetable_names)]
            second = vegetable_names[(protein_index + 1) % len(vegetable_names)]
            third = vegetable_names[(protein_index + 2) % len(vegetable_names)]
            bundles = [[first], [first, second] if first != second else [first], [third]]
        else:
            bundles = [[]]
        for variant, bundle in enumerate(bundles):
            request = dict(engine_request)
            request["protein_name"] = protein.name
            request["protein_state"] = _protein_state(protein)
            request["vegetable_names"] = bundle
            request["vegetable_name"] = bundle[0] if bundle else ""
            request["foundation_name"] = (
                foundations[(protein_index + variant) % len(foundations)]
                if foundations and variant != 1 else ""
            )
            request["cuisine_name"] = flavor_directions[(protein_index + variant) % len(flavor_directions)]
            request["meal_structure"] = (
                "composed_plate" if variant == 1
                else "layered_bowl" if variant == 2 and request["foundation_name"]
                else "integrated"
            )
            # Canned/cooked protein plus skillet vegetables is ordinarily a
            # warm-together pantry meal. Do not manufacture restaurant-style
            # separation when no distinct entree treatment supports it.
            if (
                request["meal_structure"] == "composed_plate"
                and _protein_state(protein) in {"Canned", "Cooked", "Ready to Eat"}
            ):
                request["meal_structure"] = "integrated"
            signature = (
                _key(protein.name), tuple(sorted(_key(item) for item in bundle)),
                _key(request["foundation_name"]), _key(request["cuisine_name"]),
                request["meal_structure"],
            )
            if signature in seen:
                continue
            seen.add(signature)
            concepts.append((request, protein))

    # One-protein kitchens still deserve several substantially different ideas.
    if len(proteins) == 1:
        protein = proteins[0]
        for index, vegetable in enumerate(vegetable_names[3:6], start=3):
            request = dict(engine_request)
            request.update({
                "protein_name": protein.name,
                "protein_state": _protein_state(protein),
                "vegetable_names": [vegetable],
                "vegetable_name": vegetable,
                "foundation_name": foundations[index % len(foundations)] if foundations else "",
                "cuisine_name": flavor_directions[index % len(flavor_directions)],
            })
            concepts.append((request, protein))

    return concepts[:48]


def _method_preferences(protein: ResolvedIngredient | None) -> tuple[str, ...]:
    state = _protein_state(protein)
    behavior = resolve_behavior(
        protein.name, "protein", protein.form_name or "", db_path=DB_PATH
    ) if protein else None
    family_code = behavior.primary_family.code if behavior and behavior.primary_family else ""
    if family_code == "egg":
        return ("skillet", "casserole", "handheld", "soup", "grill")
    if family_code in {"legume", "prepared_legume"}:
        return ("soup", "skillet", "casserole", "handheld", "grill")
    if state == "Cooked":
        return ("casserole", "handheld", "soup", "skillet", "grill")
    return ("skillet", "grill", "casserole", "soup", "handheld")


def _choose_concept_candidate(options, protein, used_methods):
    supported = {
        item.get("cooking_method", item.get("strategy")): item
        for item in options
        if item.get("cooking_method", item.get("strategy")) in _LIVE_PLANNER_METHODS
    }
    preferences = _method_preferences(protein)
    for method in preferences:
        if method in supported and method not in used_methods:
            return supported[method]
    for method in preferences:
        if method in supported:
            return supported[method]
    return next(iter(supported.values()), None)


def _idea_method_attempts(protein, concept_index: int, meal_structure: str) -> tuple[str, ...]:
    """Order a concept's methods without constructing every possible recipe.

    Phase 2 needs enough fully validated meals to choose an assortment; it
    does not need a complete cooking schedule for every method of every
    ingredient bundle.  Rotate the preferred method by concept so the pool
    retains variety, and let the caller fall through only when that method is
    not trained for the selected components or equipment.
    """
    preferences = _method_preferences(protein)
    structure = _clean(meal_structure) or "integrated"
    if structure != "integrated":
        preferences = tuple(
            method for method in preferences if method in {"skillet", "grill"}
        )
    if not preferences:
        return ()
    offset = concept_index % len(preferences)
    return preferences[offset:] + preferences[:offset]


def _dish_family(candidate: dict) -> str:
    structure = _clean(candidate.get("meal_structure")) or "integrated"
    if structure == "composed_plate":
        return "composed_plate"
    if structure == "layered_bowl":
        return "layered_bowl"
    method = _clean(candidate.get("cooking_method", candidate.get("strategy")))
    protein_behavior = resolve_behavior(
        candidate.get("protein"), "protein", candidate.get("protein_state") or "",
        method, DB_PATH,
    )
    family_code = protein_behavior.primary_family.code if protein_behavior.primary_family else ""
    physical = set(protein_behavior.primary_family.physical_traits) if protein_behavior.primary_family else set()
    cuisine = _key(candidate.get("cuisine"))
    if method == "skillet":
        if "chinese" in cuisine:
            return "stir_fry"
        if family_code == "tender_steak":
            return "seared_dinner"
        if "ground" in physical:
            return "hash"
        if family_code in {"legume", "prepared_legume", "ready_protein"}:
            return "pantry_supper"
        return "skillet_supper" if candidate.get("foundation") else "one_pot_supper"
    if method == "soup":
        return "bean_soup" if family_code in {"legume", "prepared_legume"} else "rustic_soup"
    if method == "braise":
        return "slow_braise"
    if method == "oven_braise":
        return "oven_braise"
    if method == "casserole":
        return "baked_casserole"
    if method == "handheld":
        return "wrap_or_sandwich"
    return method or "meal"


_FAMILY_LABELS = {
    "stir_fry": "Stir-Fry",
    "seared_dinner": "Seared Dinner",
    "hash": "Hash",
    "pantry_supper": "Pantry Supper",
    "one_pot_supper": "One-Pot Supper",
    "skillet_supper": "Skillet Supper",
    "bean_soup": "Bean Soup",
    "rustic_soup": "Rustic Soup",
    "slow_braise": "Slow Braise",
    "oven_braise": "Oven Braise",
    "baked_casserole": "Casserole",
    "wrap_or_sandwich": "Wrap or Sandwich",
    "composed_plate": "Composed Plate",
    "layered_bowl": "Layered Bowl",
}


_PRODUCTION_LABELS = {
    "one_vessel": "One vessel",
    "multi_component": "Multi-component",
    "component_assembly": "Cook, then assemble",
}


def _production_strategy(candidate: dict) -> str:
    structure = _clean(candidate.get("meal_structure")) or "integrated"
    method = _clean(candidate.get("cooking_method", candidate.get("strategy")))
    if structure == "composed_plate":
        return "multi_component"
    if structure == "layered_bowl" or method == "handheld":
        return "component_assembly"
    return "one_vessel"


def _heat_source(candidate: dict) -> str:
    method = _clean(candidate.get("cooking_method", candidate.get("strategy")))
    if method in {"casserole", "oven_braise"}:
        return "oven"
    if method == "handheld":
        return "mixed"
    if method == "grill":
        return "grill"
    return "stovetop"


def _selection_title(candidate: dict) -> str:
    proteins = [
        item.get("name") for item in candidate.get("proteins") or []
        if isinstance(item, dict)
    ]
    ingredients = [*(proteins or [candidate.get("protein")]), *str(candidate.get("vegetable") or "").split(" & ")]
    planned_side = next((
        component.get("name") for component in
        (candidate.get("component_plan") or {}).get("components") or []
        if component.get("role") == "side"
    ), None)
    structure = _clean(candidate.get("meal_structure")) or "integrated"
    if structure in {"composed_plate", "layered_bowl"}:
        ingredients.append(planned_side or candidate.get("foundation"))
    ingredients = [_clean(item) for item in ingredients if _clean(item)]
    if len(ingredients) > 1:
        components = f"{', '.join(ingredients[:-1])} & {ingredients[-1]}"
    else:
        components = ingredients[0] if ingredients else "My Kitchen"
    cuisine = _clean(candidate.get("cuisine"))
    prefix = "" if cuisine in {"", "Comfort Food", "American"} else f"{cuisine} "
    family = _FAMILY_LABELS.get(candidate.get("dish_family"), _clean(candidate.get("label")) or "Meal")
    foundation = _clean(planned_side or candidate.get("foundation"))
    with_foundation = (
        f" with {foundation}"
        if foundation and structure == "integrated" and family not in {"Casserole", "Bean Soup", "Rustic Soup"}
        else ""
    )
    return f"{prefix}{components} {family}{with_foundation}"


def _effort_label(score) -> str:
    value = int(score or 0)
    if value <= 3:
        return "Very low"
    if value <= 5:
        return "Low"
    if value <= 7:
        return "Moderate"
    return "High"


def _effort_target(level) -> int:
    return {"Very Low": 3, "Low": 5, "Medium": 7, "High": 10}.get(_clean(level), 6)


_GENERATOR_REQUEST_FIELDS = {
    "protein_name", "protein_names", "protein_states", "protein_roles",
    "vegetable_name", "foundation_name", "cuisine_name",
    "energy_level", "budget_level", "time_minutes", "servings", "max_results",
    "vegetable_names", "protein_state", "available_items", "requested_items",
    "available_equipment", "excluded_items", "planned_purchase_items",
    "requested_method", "selected_extras", "component_forms", "meal_structure",
    "inventory_lots", "eater_profiles", "use_all_cans", "cooking_for_kids",
    "kid_theme", "component_methods",
}


def _generator_request(request: dict) -> dict:
    """Keep selection-only context out of the recipe engine contract."""
    return {key: value for key, value in request.items() if key in _GENERATOR_REQUEST_FIELDS}


def _recent_match_penalty(candidate: dict, recent_meals: list) -> int:
    penalty = 0
    for age, meal in enumerate(recent_meals[:8]):
        if not isinstance(meal, dict):
            continue
        weight = max(1, 8 - age)
        if _key(meal.get("title")) == _key(candidate.get("title")):
            penalty += 7 * weight
        elif (
            _key(meal.get("protein")) == _key(candidate.get("protein"))
            and _key(meal.get("dish_family")) == _key(candidate.get("dish_family"))
        ):
            penalty += 4 * weight
    return penalty


def _score_make_candidate(candidate: dict, engine_request: dict) -> dict:
    effort = int(candidate.get("effort_score") or 0)
    effort_level = _clean(engine_request.get("effort_level") or engine_request.get("energy_level"))
    effort_target = _effort_target(effort_level)
    score = int(candidate.get("score") or 0)
    reasons = []
    if effort <= effort_target:
        score += 12 + (effort_target - effort) * 3
        reasons.append(f"{_effort_label(effort).lower()} effort for tonight")
    else:
        score -= (effort - effort_target) * 18
        reasons.append(f"above tonight’s {_clean(effort_level).lower()}-effort target")

    missing = len(candidate.get("inventory_need") or [])
    # A missing staple with a trained omission/substitution should matter, but
    # should not erase a much better culinary form (for example beans as soup).
    score -= missing * 8
    if not missing:
        score += 12
        reasons.append("uses what is already in My Kitchen")

    opportunities = len(candidate.get("opportunities") or [])
    if opportunities:
        score += opportunities * 6
        reasons.append("has a trained flavor or texture opportunity")

    if _clean(candidate.get("foundation")):
        score += 20
        reasons.append("builds a complete meal with the available side")

    method = _clean(candidate.get("cooking_method", candidate.get("strategy")))
    protein_behavior = resolve_behavior(
        candidate.get("protein"), "protein", candidate.get("protein_state") or "",
        method, DB_PATH,
    )
    if protein_behavior.primary_family and protein_behavior.method:
        score += 20
        reasons.append("the method fits the protein")
        relationships = set(protein_behavior.primary_family.relationship_traits)
        if method == "soup" and "soup-friendly" in relationships:
            score += 18
            reasons.append("the protein is especially well suited to soup")
    if candidate.get("protein_state") in {"Cooked", "Canned"} and effort_level in {"Very Low", "Low"}:
        score += 8
        reasons.append("starts with a cooked or canned protein")

    selected = {_key(candidate.get("protein")), _key(candidate.get("foundation"))}
    selected.update(_key(item) for item in str(candidate.get("vegetable") or "").split(" & "))
    use_soon = []
    for lot in engine_request.get("inventory_lots") or []:
        if _key(lot.get("name")) not in selected:
            continue
        opened = bool(lot.get("opened_at"))
        expiring = False
        try:
            expires = date.fromisoformat(_clean(lot.get("expiration_date")))
            expiring = 0 <= (expires - date.today()).days <= 3
        except (TypeError, ValueError):
            pass
        if opened or expiring:
            use_soon.append(_clean(lot.get("name")))
    if use_soon:
        score += min(24, 10 * len(use_soon))
        reasons.append(f"uses soon: {', '.join(use_soon)}")

    score -= _recent_match_penalty(candidate, engine_request.get("recent_meals") or [])
    if candidate.get("quantity_note") and "short" in _key(candidate.get("quantity_note")):
        score -= 12
    candidate["selection_score"] = score
    candidate["selection_reasons"] = reasons
    candidate["effort_label"] = _effort_label(effort)
    return candidate


def _select_assortment(pool: list[dict], limit: int) -> list[dict]:
    """Choose a useful set, not merely the first N individually ranked meals."""
    if not pool or limit <= 0:
        return []
    unique = {}
    for candidate in pool:
        signature = (
            _key(candidate.get("protein")),
            tuple(sorted(_key(item) for item in str(candidate.get("vegetable") or "").split(" & ") if _key(item))),
            _key(candidate.get("foundation")), _key(candidate.get("dish_family")),
            _key(candidate.get("cuisine")), _key(candidate.get("meal_structure")),
        )
        current = unique.get(signature)
        if current is None or candidate["selection_score"] > current["selection_score"]:
            unique[signature] = candidate
    remaining = list(unique.values())
    selected = []

    def add(candidate, badge):
        candidate["selection_badge"] = badge
        selected.append(candidate)
        remaining.remove(candidate)

    best = max(remaining, key=lambda item: item["selection_score"])
    add(best, "Best fit")
    if remaining and len(selected) < limit:
        easiest = min(
            remaining,
            key=lambda item: (item.get("effort_score", 10), -item["selection_score"]),
        )
        add(easiest, "Lowest effort")
    use_soon = [item for item in remaining if any("uses soon:" in reason for reason in item.get("selection_reasons") or [])]
    if use_soon and len(selected) < limit:
        add(max(use_soon, key=lambda item: item["selection_score"]), "Use soon")
    cooked_together_stovetop = [
        item for item in remaining
        if _clean(item.get("cooking_method", item.get("strategy"))) == "skillet"
        and (_clean(item.get("meal_structure")) or "integrated") == "integrated"
    ]
    if cooked_together_stovetop and len(selected) < limit:
        candidate = max(cooked_together_stovetop, key=lambda item: item["selection_score"])
        add(candidate, _FAMILY_LABELS.get(candidate.get("dish_family"), "Cooked together"))

    while remaining and len(selected) < limit:
        family_counts = {}
        method_counts = {}
        protein_counts = {}
        structure_counts = {}
        bundles = set()
        for item in selected:
            family_counts[item.get("dish_family")] = family_counts.get(item.get("dish_family"), 0) + 1
            method = item.get("cooking_method", item.get("strategy"))
            method_counts[method] = method_counts.get(method, 0) + 1
            protein_counts[_key(item.get("protein"))] = protein_counts.get(_key(item.get("protein")), 0) + 1
            structure = _clean(item.get("meal_structure")) or "integrated"
            structure_counts[structure] = structure_counts.get(structure, 0) + 1
            bundles.add((
                _key(item.get("protein")),
                tuple(sorted(_key(part) for part in str(item.get("vegetable") or "").split(" & ") if _key(part))),
                _key(item.get("foundation")),
            ))

        def assortment_value(item):
            value = item["selection_score"]
            value -= family_counts.get(item.get("dish_family"), 0) * 28
            value -= method_counts.get(item.get("cooking_method", item.get("strategy")), 0) * 14
            value -= protein_counts.get(_key(item.get("protein")), 0) * 16
            structure = _clean(item.get("meal_structure")) or "integrated"
            value -= structure_counts.get(structure, 0) * 10
            if structure not in structure_counts and structure != "integrated":
                value += 20
            if _key(item.get("protein")) not in protein_counts:
                value += 100
            bundle = (
                _key(item.get("protein")),
                tuple(sorted(_key(part) for part in str(item.get("vegetable") or "").split(" & ") if _key(part))),
                _key(item.get("foundation")),
            )
            if bundle in bundles:
                value -= 45
            return value

        candidate = max(remaining, key=assortment_value)
        structure = _clean(candidate.get("meal_structure")) or "integrated"
        used_badges = {item.get("selection_badge") for item in selected}
        if structure == "composed_plate":
            badge = "Composed plate" if "Composed plate" not in used_badges else f"{_clean(candidate.get('protein'))} plate"
        elif structure == "layered_bowl":
            badge = "Layered bowl" if "Layered bowl" not in used_badges else f"{_clean(candidate.get('protein'))} bowl"
        else:
            family = _FAMILY_LABELS.get(candidate.get("dish_family"), "Another idea")
            badge = family if family not in used_badges else _clean(candidate.get("protein")) or "Another idea"
        add(candidate, badge)
    return selected


def _concept_title(candidate: dict) -> str:
    components = []
    for item in (
        candidate.get("protein"),
        *str(candidate.get("vegetable") or "").split(" & "),
        candidate.get("foundation"),
    ):
        name = _clean(item)
        if name and name not in components:
            components.append(name)
    if len(components) > 1:
        component_text = f"{', '.join(components[:-1])} & {components[-1]}"
    else:
        component_text = components[0] if components else "My Kitchen"
    structure = _clean(candidate.get("meal_structure"))
    if structure == "composed_plate":
        return component_text
    if structure == "layered_bowl":
        return f"{component_text} Bowl"
    method = candidate.get("cooking_method", candidate.get("strategy", "meal"))
    endings = {
        "skillet": "Skillet",
        "casserole": "Casserole",
        "soup": "Soup",
        "handheld": "Wrap or Sandwich",
        "braise": "Stovetop Braise",
        "oven_braise": "Oven Braise",
    }
    return f"{component_text} {endings.get(method, 'Meal')}"


def _candidate_ingredients(candidate: dict) -> list[str]:
    ingredients = []
    coherence_omissions = {_key(item) for item in candidate.get("coherence_omissions") or []}
    proteins = [
        item.get("name") for item in candidate.get("proteins") or []
        if isinstance(item, dict)
    ]
    for item in (
        *(proteins or [candidate.get("protein")]),
        *str(candidate.get("vegetable") or "").split(" & "),
        candidate.get("foundation"),
    ):
        name = _clean(item)
        if name and _key(name) not in coherence_omissions and name not in ingredients:
            ingredients.append(name)

    method = candidate.get("cooking_method", candidate.get("strategy"))
    support_terms = {
        "soup": ("broth", "stock", "bouillon", "soup base", "consomme"),
        "handheld": ("bread", "bun", "roll", "tortilla", "wrap", "pita", "naan"),
    }.get(method, ())
    for available in candidate.get("inventory_have") or []:
        if support_terms and any(term in _key(available) for term in support_terms):
            if available not in ingredients:
                ingredients.append(available)
            break

    for requirement in candidate.get("inventory_requirements") or []:
        if isinstance(requirement, dict):
            status = requirement.get("status")
            if status == "Omit":
                continue
            name = _clean(
                requirement.get("resolved_name")
                if status == "Substitute"
                else requirement.get("name")
            )
            if name.lower().startswith("rendered fat from"):
                continue
        else:
            name = _clean(requirement)
        if name and _key(name) not in coherence_omissions and not any(_key(existing) == _key(name) for existing in ingredients):
            ingredients.append(name)
    return ingredients


def _candidate_ingredient_lines(
    candidate: dict,
    resolved: list[ResolvedIngredient],
) -> list[str]:
    """Render selected components and recipe requirements with useful state."""
    requirements = {}
    for item in candidate.get("inventory_requirements") or []:
        if not isinstance(item, dict) or not _clean(item.get("name")):
            continue
        requirements[_key(item.get("name"))] = item
        if _clean(item.get("resolved_name")):
            requirements[_key(item.get("resolved_name"))] = item
    resolved_by_name = {}
    for item in resolved:
        resolved_by_name.setdefault(_key(item.name), item)

    protein_states = {
        _key(item.get("name")): _clean(item.get("state"))
        for item in candidate.get("proteins") or [] if isinstance(item, dict)
    }
    protein_key = _key(candidate.get("protein"))
    lines = []
    seen = set()
    for name in _candidate_ingredients(candidate):
        key = _key(name)
        if not key or key in seen:
            continue
        seen.add(key)

        details = []
        resolved_item = resolved_by_name.get(key)
        if key in protein_states:
            details.append(protein_states[key])
        elif key == protein_key and _clean(candidate.get("protein_state")):
            details.append(_clean(candidate.get("protein_state")))
        elif resolved_item and _clean(resolved_item.form_name):
            form_name = _clean(resolved_item.form_name)
            if form_name.lower().replace("-", " ") != "shelf stable":
                details.append(form_name)

        requirement = requirements.get(key)
        planned = (candidate.get("quantity_plan") or {}).get(key, {})
        quantity = _clean(planned.get("display")) or (_clean(requirement.get("quantity")) if requirement else "")
        if "lime" in name.lower() and "lemon" in quantity.lower():
            quantity = quantity.lower().replace("lemons", "lime").replace("lemon", "lime")
        elif "lemon" in name.lower() and "lime" in quantity.lower():
            quantity = quantity.lower().replace("limes", "lemon").replace("lime", "lemon")
        if float(planned.get("shortfall") or 0) > 0:
            available = float(planned.get("available") or 0)
            target = float(planned.get("planned") or 0)
            quantity = f"{available:g} on hand · {target:g} planned"
        if quantity:
            details.append(quantity)

        lines.append(f"{name} — {' · '.join(details)}" if details else name)
    return lines


def _candidate_view(candidate: dict) -> dict:
    method = _clean(candidate.get("cooking_method", candidate.get("strategy")))
    candidate_id = _clean(candidate.get("candidate_id")) or method or "candidate"
    meal_structure = _clean(candidate.get("meal_structure")) or "integrated"
    production_strategy = _production_strategy(candidate)
    meal_shape = (
        "bowl" if meal_structure == "layered_bowl"
        else "plate" if meal_structure == "composed_plate"
        else _MEAL_SHAPES.get(method, "plate")
    )
    return {
        "candidate_id": candidate_id,
        "id": candidate_id,
        "title": candidate.get("title") or candidate.get("label") or "Stock & Stir meal",
        "meal_shape": meal_shape,
        "meal_structure": meal_structure,
        "component_methods": dict(candidate.get("component_methods") or {}),
        "production_strategy": production_strategy,
        "production_label": _PRODUCTION_LABELS[production_strategy],
        "heat_source": _heat_source(candidate),
        "equipment_strategy": "adaptive",
        "serving_temperature": "cold" if method == "cold_meal" else "hot",
        "preparation_mode": "assembled" if method in {"cold_meal", "handheld"} else "cooked",
        "meal_occasion": candidate.get("meal_occasion") or "Any",
        "servings": candidate.get("servings", 4),
        "energy": candidate.get("energy") or "Low",
        "total_minutes": candidate.get("minutes", 0),
        "minutes": candidate.get("minutes", 0),
        "active_minutes": candidate.get("active_minutes", 0),
        "passive_minutes": candidate.get("passive_minutes", 0),
        "attention": candidate.get("attention_score", 0),
        "effort": candidate.get("effort_score", 0),
        "effort_label": candidate.get("effort_label") or _effort_label(candidate.get("effort_score")),
        "score": candidate.get("score", 0),
        "selection_score": candidate.get("selection_score", candidate.get("score", 0)),
        "selection_badge": candidate.get("selection_badge"),
        "selection_reasons": list(candidate.get("selection_reasons") or []),
        "dish_family": candidate.get("dish_family") or _dish_family(candidate),
        "protein": candidate.get("protein"),
        "proteins": list(candidate.get("proteins") or []),
        "vegetable": candidate.get("vegetable"),
        "foundation": candidate.get("foundation"),
        "cuisine": candidate.get("cuisine"),
        "cooking_method": method,
        "match": _match_text(int(candidate.get("selection_score", candidate.get("score", 0)))),
        "summary": (
            "; ".join(candidate.get("selection_reasons")[:2])
            if candidate.get("selection_reasons")
            else candidate.get("why") or "A practical meal built from My Kitchen."
        ),
        "missing_items": list(candidate.get("inventory_need") or []),
        "ingredient_adjustments": [
            item for item in candidate.get("inventory_requirements") or []
            if item.get("status") in {"Substitute", "Omit"}
        ],
        "quantity_note": candidate.get("quantity_note"),
        "cost_estimate": None,
        "capability_status": "supported",
    }


def _builder_candidates(payload: dict, db_path: str | Path):
    kitchen = payload.get("kitchen") if isinstance(payload.get("kitchen"), dict) else {}
    selections = payload.get("selections") if isinstance(payload.get("selections"), dict) else {}
    snapshot, resolved, pending, engine_request = _engine_request(kitchen, db_path)

    raw_proteins = selections.get("proteins") or []
    if isinstance(raw_proteins, (str, dict)):
        raw_proteins = [raw_proteins]
    protein_selections = []
    for index, item in enumerate(raw_proteins):
        if isinstance(item, dict):
            name = _clean(item.get("name"))
            state = _clean(item.get("state"))
            role = _clean(item.get("role"))
        else:
            name, state, role = _clean(item), "", ""
        if name and not any(_key(existing["name"]) == _key(name) for existing in protein_selections):
            protein_selections.append({"name": name, "state": state, "role": role})
    legacy_protein = _clean(selections.get("protein"))
    if not protein_selections and legacy_protein:
        protein_selections = [{
            "name": legacy_protein,
            "state": _clean(selections.get("protein_state")),
            "role": "main",
        }]
    protein = protein_selections[0]["name"] if protein_selections else ""
    produce = selections.get("produce") or []
    if isinstance(produce, str):
        produce = [produce]
    produce = [_clean(item) for item in produce if _clean(item)]
    produce_forms = selections.get("produce_forms") if isinstance(selections.get("produce_forms"), dict) else {}
    foundation = _clean(selections.get("foundation"))
    extras = selections.get("extras") or []
    if isinstance(extras, str):
        extras = [extras]
    extras = [_clean(item) for item in extras if _clean(item)]
    method = _clean(selections.get("cooking_method"))
    meal_structure = _clean(selections.get("meal_structure")) or "integrated"
    if not protein:
        raise APIContractError("Build Your Meal requires at least one protein.")
    protein_selections[0]["role"] = "main"
    for item in protein_selections[1:]:
        if not item["role"]:
            behavior = resolve_behavior(
                item["name"], "protein", item.get("state") or "", method, db_path
            )
            functions = set(behavior.primary_family.culinary_functions) if behavior.primary_family else set()
            relationships = set(behavior.primary_family.relationship_traits) if behavior.primary_family else set()
            item["role"] = (
                "stretch" if "protein-stretcher" in functions
                else "accent" if "accent-capable" in relationships
                else "supporting"
            )
    if method not in _LIVE_PLANNER_METHODS:
        raise APIContractError("Choose a currently supported cooking method.")
    if meal_structure not in {"integrated", "composed_plate", "layered_bowl"}:
        raise APIContractError("Choose a supported meal structure.")
    if method not in {"skillet", "grill"} and meal_structure != "integrated":
        raise APIContractError("That cooking method already determines an integrated meal structure.")
    if _clean(selections.get("serving_temperature")) == "cold":
        raise APIContractError("Cold meal planning is visible but is not trained yet.")

    with closing(sqlite3.connect(db_path)) as con:
        valid_proteins = {
            _key(row[0]) for row in con.execute(
                """SELECT i.name FROM proteins p JOIN ingredients i USING (ingredient_id)
                   WHERE p.verified=1 AND i.active=1"""
            ).fetchall()
        }
        valid_produce = {
            _key(row[0]) for row in con.execute(
                """SELECT i.name FROM vegetables v JOIN ingredients i USING (ingredient_id)
                   WHERE v.verified=1 AND i.active=1
                   UNION SELECT name FROM ingredients
                   WHERE active=1 AND lower(category)='fruit'"""
            ).fetchall()
        }
        valid_foundations = {
            _key(row[0]) for row in con.execute(
                "SELECT name FROM foundations WHERE verified=1"
            ).fetchall()
        }
    unknown_proteins = [item["name"] for item in protein_selections if _key(item["name"]) not in valid_proteins]
    if unknown_proteins:
        raise APIContractError(f"Unknown or untrained protein: {unknown_proteins[0]}")
    unknown_produce = [name for name in produce if _key(name) not in valid_produce]
    if unknown_produce:
        raise APIContractError(f"Unknown produce selection: {unknown_produce[0]}")
    if foundation and _key(foundation) not in valid_foundations:
        raise APIContractError(f"Unknown side: {foundation}")
    valid_extras = {_key(name) for name in _builder_extra_names(db_path)}
    unknown_extras = [name for name in extras if _key(name) not in valid_extras]
    if unknown_extras:
        raise APIContractError(f"Unknown pantry or fridge extra: {unknown_extras[0]}")

    owned_keys = {_key(item.name) for item in resolved}
    resolved_by_name = {_key(item.name): item for item in resolved}
    for item in _inventory_from(kitchen):
        raw_key = _key(item.get("name"))
        owned_keys.add(_key(_BUILDER_EXTRA_ALIASES.get(raw_key, item.get("name"))))
    selected_components = [*[item["name"] for item in protein_selections], *produce, foundation, *extras]
    # Every explicit builder selection is eligible for procurement. That
    # includes topping up an owned ingredient (for example, two steaks on
    # hand for a four-steak composed plate), not only wholly missing foods.
    planned_purchases = [name for name in selected_components if name]
    owned_protein = resolved_by_name.get(_key(protein))
    protein_states = {}
    protein_roles = {}
    for item in protein_selections:
        owned_item = resolved_by_name.get(_key(item["name"]))
        protein_states[item["name"]] = _protein_state(owned_item) if owned_item else (item["state"] or "Fresh Raw")
        protein_roles[item["name"]] = item["role"]
    if (
        any(_key(state) == "frozen raw" for state in protein_states.values())
        and selections.get("thaw_readiness_confirmed") is not True
    ):
        raise APIContractError(
            "Confirm that frozen protein will be fully thawed before Step 1, or choose another protein."
        )
    # A pantry can describe raw meat as "Refrigerated" because that is where
    # it lives. The cooking engine needs the derived culinary state instead.
    component_forms = {
        item["name"]: protein_states[item["name"]]
        for item in protein_selections
    }
    component_forms.update({
        name: resolved_by_name[_key(name)].form_name
        for name in [*produce, foundation]
        if name and _key(name) in resolved_by_name and resolved_by_name[_key(name)].form_name
    })
    for name in produce:
        if _key(name) not in resolved_by_name and _clean(produce_forms.get(name)):
            component_forms[name] = _clean(produce_forms.get(name))
    if foundation and not _clean(component_forms.get(foundation)):
        component_forms[foundation] = default_form_for(foundation, "foundation", db_path)
    engine_request.update({
        "protein_name": protein,
        "protein_names": [item["name"] for item in protein_selections],
        "protein_states": protein_states,
        "protein_roles": protein_roles,
        "protein_state": protein_states[protein],
        "vegetable_name": produce[0] if produce else "",
        "vegetable_names": produce,
        "foundation_name": foundation,
        "cuisine_name": _clean(selections.get("cuisine")) or "Comfort Food",
        "energy_level": _clean(selections.get("energy")) or "Low",
        "time_minutes": selections.get("time_minutes") or 45,
        "servings": selections.get("servings") or 4,
        "eater_profiles": selections.get("eater_profiles") or {},
        "use_all_cans": bool(selections.get("use_all_cans")),
        "max_results": 1,
        "requested_method": method,
        "planned_purchase_items": planned_purchases,
        "selected_extras": extras,
        "component_forms": component_forms,
        "component_methods": dict(selections.get("component_methods") or {}),
        "meal_structure": meal_structure,
    })
    engine_request["available_items"] = list(dict.fromkeys([
        *engine_request.get("available_items", []),
        *[name for name in extras if _key(name) in owned_keys],
    ]))
    candidates = generate_candidates(**_generator_request(engine_request))
    if not candidates:
        method_label = next(
            (item["label"] for item in _BUILDER_METHODS if item["id"] == method),
            "selected cooking environment",
        )
        conflicts = []
        for name, role, form in [
            *[(item["name"], "protein", protein_states[item["name"]]) for item in protein_selections],
            *[(name, "vegetable", component_forms.get(name, "Fresh")) for name in produce],
            *([(foundation, "foundation", component_forms.get(foundation, ""))] if foundation else []),
        ]:
            behavior = resolve_behavior(name, role, form, method, db_path)
            if behavior.primary_family and behavior.method is None:
                conflicts.append(name)
        if conflicts:
            names = ", ".join(conflicts)
            raise APIContractError(
                f"This meal needs a little adjustment. {names} does not yet have a trained "
                f"{method_label} route in the selected form. Choose another cooking environment "
                "or change that ingredient."
            )
        excluded = {_key(item) for item in engine_request.get("excluded_items", [])}
        blocked = [name for name in selected_components if name and _key(name) in excluded]
        if blocked:
            raise APIContractError(
                f"This meal includes {', '.join(blocked)}, which is listed in My Kitchen exclusions. "
                "Remove it or choose a suitable replacement."
            )
        raise APIContractError(
            "This combination does not have a complete trained cooking route yet. "
            "Try changing the cooking environment or one ingredient."
        )
    candidate = candidates[0]
    # Small scheduling overruns are estimates and should not reject an
    # otherwise valid ordinary meal. A material shortfall (the long-cook case
    # this guard exists for) needs an explicit planning-ahead resolution.
    if not candidate.get("time_feasible", True) and int(candidate.get("time_shortfall_minutes") or 0) >= 15:
        required = int(candidate.get("required_lead_minutes") or candidate.get("minutes") or 0)
        available = int(engine_request["time_minutes"])
        raise APIContractError(
            f"This meal needs a little more time. It requires about {required} minutes, "
            f"but you selected {available} minutes. Choose a Planning ahead time, use a "
            "trained faster method, or select a quicker-cooking protein."
        )
    candidate["candidate_id"] = "-".join((
        "build", _slug(engine_request["meal_structure"]),
        _slug(candidate.get("cooking_method") or method), _slug(protein),
        _slug("-".join(produce)) or "no-produce",
        _slug(foundation) or "no-foundation",
    ))
    candidate["dish_family"] = _dish_family(candidate)
    candidate["title"] = _selection_title(candidate)
    candidate["meal_occasion"] = _clean(selections.get("meal_occasion")) or "Any"
    candidate["serving_temperature"] = "hot"
    return snapshot, resolved, pending, [candidate], engine_request


def _raw_candidates(payload: dict, db_path: str | Path):
    if _clean(payload.get("mode")) == "build_your_meal":
        return _builder_candidates(payload, db_path)
    snapshot, resolved, pending, engine_request = _engine_request(payload, db_path)
    if not any((
        engine_request["protein_name"],
        engine_request["vegetable_names"],
        engine_request["foundation_name"],
    )):
        return snapshot, resolved, pending, [], engine_request
    pool = []
    max_results = min(6, max(1, int(engine_request.get("max_results") or 6)))
    for index, (concept_request, protein) in enumerate(
        _concept_requests(engine_request, resolved)
    ):
        options = []
        for requested_method in _idea_method_attempts(
            protein, index, concept_request.get("meal_structure"),
        ):
            method_request = dict(concept_request)
            method_request["requested_method"] = requested_method
            options = generate_candidates(**_generator_request(method_request))
            if options:
                break
        for option_index, candidate in enumerate(options):
            method = candidate.get("cooking_method", candidate.get("strategy", "meal"))
            if method not in _LIVE_PLANNER_METHODS:
                continue
            if method not in {"skillet", "grill"} and _clean(candidate.get("meal_structure")) not in {"", "integrated"}:
                continue
            candidate["dish_family"] = _dish_family(candidate)
            candidate["title"] = _selection_title(candidate)
            candidate["candidate_id"] = "-".join(filter(None, (
                _slug(method), _slug(candidate.get("protein", "pantry")),
                _slug(candidate.get("vegetable")), _slug(candidate.get("foundation")),
                _slug(candidate.get("cuisine")), str(index + 1), str(option_index + 1),
            )))
            pool.append(_score_make_candidate(candidate, engine_request))
    # Do not manufacture variety by offering a meal wildly above tonight's
    # stated capacity. A small stretch remains visible; a different kind of
    # evening should not.
    effort_ceiling = _effort_target(engine_request.get("effort_level")) + 4
    within_effort = [item for item in pool if int(item.get("effort_score") or 0) <= effort_ceiling]
    if within_effort:
        pool = within_effort
    candidates = _select_assortment(pool, max_results)
    return snapshot, resolved, pending, candidates, engine_request


def get_recipe_list(payload: dict, db_path: str | Path = DB_PATH) -> dict:
    """Create web-safe candidate summaries from the current planner."""
    snapshot, _resolved, pending, candidates, _request = _raw_candidates(payload, db_path)
    notices = []
    if pending:
        notices.append({
            "code": "unmatched_inventory",
            "message": "Some kitchen items are not in the current CKB yet.",
            "items": [item["name"] for item in pending],
        })
    if snapshot.get("cost_filter"):
        notices.append({
            "code": "cost_estimate_unavailable",
            "message": "Cost filtering is reserved in API v1 but is not trained yet.",
        })
    if not candidates:
        notices.append({
            "code": "no_trained_components",
            "message": "The current engine could not identify a trained meal component.",
        })
    views = [_candidate_view(candidate) for candidate in candidates]
    return {
        "api_version": CONTRACT_VERSION,
        "household_id": snapshot.get("household_id"),
        "candidates": views,
        # Temporary compatibility alias for the existing static prototype.
        "recipes": views,
        "notices": notices,
    }


def get_recipe(payload: dict, db_path: str | Path = DB_PATH) -> dict:
    """Rebuild and return the selected current-engine recipe without server memory."""
    candidate_id = _clean(payload.get("candidate_id", payload.get("recipe_id")))
    kitchen = payload.get("kitchen") if isinstance(payload.get("kitchen"), dict) else payload
    _snapshot, resolved, _pending, candidates, _request = _raw_candidates(kitchen, db_path)
    candidate = next(
        (item for item in candidates if _clean(item.get("candidate_id")) == candidate_id),
        None,
    )
    if not candidate:
        raise APIContractError(f"Unknown or unavailable candidate_id: {candidate_id}")
    recipe = build_recipe_from_candidate(candidate)
    classification = _candidate_view(candidate)
    ingredients = _candidate_ingredient_lines(candidate, resolved)
    provenance = public_build_provenance(DEPLOYED_BUILD_PROVENANCE, {
        "api_contract": CONTRACT_VERSION,
        "candidate_id": candidate_id,
        "cooking_method": candidate.get("cooking_method", candidate.get("strategy")),
        "meal_structure": candidate.get("meal_structure"),
        "energy": _request.get("energy_level"),
        "equipment": _request.get("available_equipment") or [],
        "protein_state": _request.get("protein_state"),
        "servings": _request.get("servings"),
        "time_limit_minutes": _request.get("time_minutes"),
    })
    missing_items = [
        item["name"]
        for item in recipe.get("inventory_requirements") or []
        if item.get("status") in {"Need", "Short"} and item.get("required", True)
    ]
    return {
        "api_version": CONTRACT_VERSION,
        "candidate_id": candidate_id,
        "id": candidate_id,
        "title": recipe.get("name") or classification["title"],
        "summary": recipe.get("summary") or classification["summary"],
        "ingredients": ingredients,
        "equipment": list(recipe.get("equipment") or []),
        "steps": list(recipe.get("action_steps") or []),
        "instructions": list(recipe.get("instructions") or []),
        "plan_items": list(recipe.get("plan_items") or []),
        "component_plan": dict(recipe.get("component_plan") or {}),
        "total_minutes": classification["total_minutes"],
        "active_minutes": classification["active_minutes"],
        "passive_minutes": classification["passive_minutes"],
        "meal_shape": classification["meal_shape"],
        "meal_structure": classification["meal_structure"],
        "production_strategy": classification["production_strategy"],
        "production_label": classification["production_label"],
        "heat_source": classification["heat_source"],
        "equipment_strategy": classification["equipment_strategy"],
        "serving_temperature": classification["serving_temperature"],
        "preparation_mode": classification["preparation_mode"],
        "meal_occasion": classification["meal_occasion"],
        "dish_family": classification.get("dish_family"),
        "protein": classification.get("protein"),
        "cuisine": classification.get("cuisine"),
        "cooking_method": classification.get("cooking_method"),
        "effort": classification.get("effort"),
        "effort_label": classification.get("effort_label"),
        "cost_estimate": None,
        "capability_status": "supported",
        "grocery_list": list(recipe.get("grocery_list") or []),
        "missing_items": missing_items,
        "inventory_requirements": list(recipe.get("inventory_requirements") or []),
        "ingredient_adjustments": [
            item for item in recipe.get("inventory_requirements") or []
            if item.get("status") in {"Substitute", "Omit"}
        ] + [
            {
                "name": item,
                "status": "Omit",
                "omission_consequence": "It does not support the selected cuisine and meal identity.",
            }
            for item in recipe.get("coherence_omissions") or []
        ],
        "quantity_note": recipe.get("quantity_note") or "",
        "recipe_validation": recipe.get("validation") or {},
        "serving_styles": list(recipe.get("serving_styles") or []),
        "serving_style": candidate.get("serving_style"),
        "build_provenance": provenance,
    }
