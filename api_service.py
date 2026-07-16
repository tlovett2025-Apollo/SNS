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

from config import DB_PATH
from build_provenance import collect_build_provenance
from household_inventory import replace_household_inventory, submit_pending_items
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
}

_LIVE_PLANNER_METHODS = {"skillet", "casserole", "soup", "handheld"}

_BUILDER_METHODS = (
    {"id": "skillet", "label": "Skillet", "description": "One-pan stovetop meal."},
    {"id": "soup", "label": "Soup", "description": "A broth-based meal in one pot."},
    {"id": "casserole", "label": "Casserole", "description": "An oven-baked family-style meal."},
    {"id": "handheld", "label": "Wrap or Sandwich", "description": "A handheld meal with a bread or wrap foundation."},
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
_BUILDER_EXTRA_ALIASES = {"mayo": "Mayonnaise"}

_PROTEIN_CATEGORIES = {
    "beans", "beef", "chicken", "eggs", "plant protein", "pork", "processed meat",
    "protein", "seafood", "turkey",
}


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
            "name": _clean(item.get("name")),
            "form": _clean(item.get("form")) or None,
            "storage_location": _clean(
                item.get("storage_location", item.get("storage"))
            ) or None,
            "quantity": quantity,
            "unit": _clean(item.get("unit")) or None,
            "quantity_band": band,
            "origin": _clean(item.get("origin")) or "manual",
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


def resolve_inventory(payload: dict, db_path: str | Path = DB_PATH) -> tuple[list[ResolvedIngredient], list[dict]]:
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
            form = _form_row(con, int(row["ingredient_id"]), item["form"])
            resolved.append(ResolvedIngredient(
                ingredient_id=int(row["ingredient_id"]),
                name=str(row["name"]),
                category=str(row["category"]),
                form_id=int(form["form_id"]) if form else None,
                form_name=str(form["form_name"]) if form else item["form"],
                source=item,
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

    def choice(name: str, **extra) -> dict:
        inventory_item = resolved_by_name.get(_key(name))
        return {
            "name": name,
            "owned": _key(name) in owned,
            "form": inventory_item.form_name if inventory_item else None,
            **extra,
        }

    return {
        "api_version": CONTRACT_VERSION,
        "proteins": [choice(row["name"]) for row in proteins],
        "produce": [choice(row["name"], kind=row["kind"]) for row in produce],
        "foundations": [choice(row["name"]) for row in foundations],
        "extras": [choice(name) for name in _BUILDER_EXTRA_NAMES],
        "cuisines": [row["name"] for row in cuisines],
        "methods": list(_BUILDER_METHODS),
        "meal_structures": [
            {"id": "integrated", "label": "Cooked Together", "description": "A cohesive skillet, pot, soup, or casserole."},
            {"id": "composed_plate", "label": "Composed Plate", "description": "Restaurant-style: protein, vegetable, and foundation prepared independently."},
            {"id": "layered_bowl", "label": "Layered Bowl", "description": "A foundation with components arranged or spooned over it."},
        ],
        "serving_temperatures": [
            {"id": "hot", "label": "Hot", "available": True},
            {"id": "cold", "label": "Cold", "available": False,
             "note": "Cold meal planning is the next cooking grammar being trained."},
        ],
        "meal_occasions": ["Breakfast", "Lunch", "Dinner", "Any"],
    }


def save_my_kitchen(
    payload: dict,
    *,
    household_id: int,
    acting_user_id: int,
    db_path: str | Path = DB_PATH,
) -> dict:
    """Persist a kitchen after a trusted HTTP/auth layer resolves membership."""
    resolved, pending = resolve_inventory(payload, db_path)
    items = [{
        "ingredient_id": item.ingredient_id,
        "form_id": item.form_id,
        "quantity": item.source.get("quantity"),
        "unit": item.source.get("unit"),
        "storage_location": item.source.get("storage_location"),
        "quantity_band": item.source.get("quantity_band"),
        "origin": item.source.get("origin") or "manual",
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
    """Build distinct ingredient concepts before asking the planner for methods."""
    proteins = [
        item for item in resolved if _key(item.category) in _PROTEIN_CATEGORIES
    ]
    vegetables = [item for item in resolved if _key(item.category) == "vegetables"]
    foundation = engine_request.get("foundation_name", "")

    if not proteins:
        return [(dict(engine_request), None)]

    concepts = []
    for index, protein in enumerate(proteins):
        request = dict(engine_request)
        request["protein_name"] = protein.name
        request["protein_state"] = _protein_state(protein)

        if vegetables:
            if len(proteins) > 1 and index % 3 == 0 and len(vegetables) > 1:
                selected_vegetables = vegetables[:2]
            else:
                selected_vegetables = [vegetables[index % len(vegetables)]]
        else:
            selected_vegetables = []
        request["vegetable_names"] = [item.name for item in selected_vegetables]
        request["vegetable_name"] = (
            selected_vegetables[0].name if selected_vegetables else ""
        )
        request["foundation_name"] = foundation if index % 2 == 0 else ""
        concepts.append((request, protein))

    # A kitchen with one protein can still offer distinct vegetable-centered
    # ideas instead of repeating one ingredient bundle under several methods.
    if len(proteins) == 1 and len(vegetables) > 1:
        for vegetable in vegetables[1:]:
            request = dict(engine_request)
            request["protein_name"] = proteins[0].name
            request["protein_state"] = _protein_state(proteins[0])
            request["vegetable_names"] = [vegetable.name]
            request["vegetable_name"] = vegetable.name
            request["foundation_name"] = ""
            concepts.append((request, proteins[0]))

    return concepts


def _method_preferences(protein: ResolvedIngredient | None) -> tuple[str, ...]:
    category = _key(protein.category if protein else "")
    state = _protein_state(protein)
    if category == "eggs":
        return ("skillet", "casserole", "handheld", "soup")
    if category == "beans":
        return ("soup", "skillet", "casserole", "handheld")
    if state == "Cooked":
        return ("casserole", "handheld", "soup", "skillet")
    return ("skillet", "casserole", "soup", "handheld")


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
    method = candidate.get("cooking_method", candidate.get("strategy", "meal"))
    endings = {
        "skillet": "Skillet",
        "casserole": "Casserole",
        "soup": "Soup",
        "handheld": "Wrap or Sandwich",
    }
    return f"{component_text} {endings.get(method, 'Meal')}"


def _candidate_ingredients(candidate: dict) -> list[str]:
    ingredients = []
    for item in (
        candidate.get("protein"),
        *str(candidate.get("vegetable") or "").split(" & "),
        candidate.get("foundation"),
    ):
        name = _clean(item)
        if name and name not in ingredients:
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
        if name and not any(_key(existing) == _key(name) for existing in ingredients):
            ingredients.append(name)
    return ingredients


def _candidate_ingredient_lines(
    candidate: dict,
    resolved: list[ResolvedIngredient],
) -> list[str]:
    """Render selected components and recipe requirements with useful state."""
    requirements = {
        _key(item.get("name")): item
        for item in candidate.get("inventory_requirements") or []
        if isinstance(item, dict) and _clean(item.get("name"))
    }
    resolved_by_name = {}
    for item in resolved:
        resolved_by_name.setdefault(_key(item.name), item)

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
        if key == protein_key and _clean(candidate.get("protein_state")):
            details.append(_clean(candidate.get("protein_state")))
        elif resolved_item and _clean(resolved_item.form_name):
            details.append(_clean(resolved_item.form_name))

        requirement = requirements.get(key)
        quantity = _clean(requirement.get("quantity")) if requirement else ""
        if quantity:
            details.append(quantity)

        lines.append(f"{name} — {' · '.join(details)}" if details else name)
    return lines


def _candidate_view(candidate: dict) -> dict:
    method = _clean(candidate.get("cooking_method", candidate.get("strategy")))
    candidate_id = _clean(candidate.get("candidate_id")) or method or "candidate"
    meal_structure = _clean(candidate.get("meal_structure")) or "integrated"
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
        "score": candidate.get("score", 0),
        "match": _match_text(int(candidate.get("score", 0))),
        "summary": candidate.get("why") or "A practical meal built from My Kitchen.",
        "missing_items": list(candidate.get("inventory_need") or []),
        "ingredient_adjustments": [
            item for item in candidate.get("inventory_requirements") or []
            if item.get("status") in {"Substitute", "Omit"}
        ],
        "cost_estimate": None,
        "capability_status": "supported",
    }


def _builder_candidates(payload: dict, db_path: str | Path):
    kitchen = payload.get("kitchen") if isinstance(payload.get("kitchen"), dict) else {}
    selections = payload.get("selections") if isinstance(payload.get("selections"), dict) else {}
    snapshot, resolved, pending, engine_request = _engine_request(kitchen, db_path)

    protein = _clean(selections.get("protein"))
    produce = selections.get("produce") or []
    if isinstance(produce, str):
        produce = [produce]
    produce = [_clean(item) for item in produce if _clean(item)]
    foundation = _clean(selections.get("foundation"))
    extras = selections.get("extras") or []
    if isinstance(extras, str):
        extras = [extras]
    extras = [_clean(item) for item in extras if _clean(item)]
    method = _clean(selections.get("cooking_method"))
    meal_structure = _clean(selections.get("meal_structure")) or "integrated"
    if not protein:
        raise APIContractError("Build Your Meal requires one protein.")
    if method not in _LIVE_PLANNER_METHODS:
        raise APIContractError("Choose a currently supported cooking method.")
    if meal_structure not in {"integrated", "composed_plate", "layered_bowl"}:
        raise APIContractError("Choose a supported meal structure.")
    if method != "skillet" and meal_structure != "integrated":
        raise APIContractError("That cooking method already determines an integrated meal structure.")
    if _clean(selections.get("serving_temperature")) == "cold":
        raise APIContractError("Cold meal planning is visible but is not trained yet.")

    with closing(sqlite3.connect(db_path)) as con:
        valid_protein = con.execute(
            """SELECT 1 FROM proteins p JOIN ingredients i USING (ingredient_id)
               WHERE p.verified=1 AND i.active=1 AND lower(i.name)=lower(?)""",
            (protein,),
        ).fetchone()
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
    if not valid_protein:
        raise APIContractError(f"Unknown or untrained protein: {protein}")
    unknown_produce = [name for name in produce if _key(name) not in valid_produce]
    if unknown_produce:
        raise APIContractError(f"Unknown produce selection: {unknown_produce[0]}")
    if foundation and _key(foundation) not in valid_foundations:
        raise APIContractError(f"Unknown foundation: {foundation}")
    valid_extras = {_key(name) for name in _BUILDER_EXTRA_NAMES}
    unknown_extras = [name for name in extras if _key(name) not in valid_extras]
    if unknown_extras:
        raise APIContractError(f"Unknown pantry or fridge extra: {unknown_extras[0]}")

    owned_keys = {_key(item.name) for item in resolved}
    resolved_by_name = {_key(item.name): item for item in resolved}
    for item in _inventory_from(kitchen):
        raw_key = _key(item.get("name"))
        owned_keys.add(_key(_BUILDER_EXTRA_ALIASES.get(raw_key, item.get("name"))))
    selected_components = [protein, *produce, foundation, *extras]
    planned_purchases = [
        name for name in selected_components if name and _key(name) not in owned_keys
    ]
    owned_protein = resolved_by_name.get(_key(protein))
    component_forms = {
        name: resolved_by_name[_key(name)].form_name
        for name in [protein, *produce, foundation]
        if name and _key(name) in resolved_by_name and resolved_by_name[_key(name)].form_name
    }
    engine_request.update({
        "protein_name": protein,
        "protein_state": _protein_state(owned_protein) if owned_protein else (_clean(selections.get("protein_state")) or "Fresh Raw"),
        "vegetable_name": produce[0] if produce else "",
        "vegetable_names": produce,
        "foundation_name": foundation,
        "cuisine_name": _clean(selections.get("cuisine")) or "Comfort Food",
        "energy_level": _clean(selections.get("energy")) or "Low",
        "time_minutes": selections.get("time_minutes") or 45,
        "servings": selections.get("servings") or 4,
        "max_results": 1,
        "requested_method": method,
        "planned_purchase_items": planned_purchases,
        "selected_extras": extras,
        "component_forms": component_forms,
        "meal_structure": meal_structure,
    })
    engine_request["available_items"] = list(dict.fromkeys([
        *engine_request.get("available_items", []),
        *[name for name in extras if _key(name) in owned_keys],
    ]))
    candidates = generate_candidates(**engine_request)
    if not candidates:
        raise APIContractError(
            "Those choices conflict with My Kitchen exclusions or the selected method."
        )
    candidate = candidates[0]
    candidate["candidate_id"] = "-".join((
        "build", _slug(engine_request["meal_structure"]), _slug(method), _slug(protein),
        _slug("-".join(produce)) or "no-produce",
        _slug(foundation) or "no-foundation",
    ))
    candidate["title"] = _concept_title(candidate)
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
    candidates = []
    used_methods = set()
    max_results = int(engine_request.get("max_results") or 10)
    for index, (concept_request, protein) in enumerate(
        _concept_requests(engine_request, resolved)
    ):
        options = generate_candidates(**concept_request)
        candidate = _choose_concept_candidate(options, protein, used_methods)
        if not candidate:
            continue
        method = candidate.get("cooking_method", candidate.get("strategy", "meal"))
        candidate["candidate_id"] = "-".join(filter(None, (
            _slug(method),
            _slug(candidate.get("protein", "pantry")),
            str(index + 1),
        )))
        candidate["title"] = _concept_title(candidate)
        used_methods.add(method)
        candidates.append(candidate)
        if len(candidates) >= max_results:
            break
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
    provenance = collect_build_provenance({
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
        if item.get("status") == "Need" and item.get("required", True)
    ]
    return {
        "api_version": CONTRACT_VERSION,
        "candidate_id": candidate_id,
        "id": candidate_id,
        "title": recipe.get("name") or classification["title"],
        "summary": recipe.get("summary") or classification["summary"],
        "ingredients": ingredients,
        "steps": list(recipe.get("action_steps") or []),
        "instructions": list(recipe.get("instructions") or []),
        "plan_items": list(recipe.get("plan_items") or []),
        "total_minutes": classification["total_minutes"],
        "meal_shape": classification["meal_shape"],
        "meal_structure": classification["meal_structure"],
        "serving_temperature": classification["serving_temperature"],
        "preparation_mode": classification["preparation_mode"],
        "meal_occasion": classification["meal_occasion"],
        "cost_estimate": None,
        "capability_status": "supported",
        "grocery_list": list(recipe.get("grocery_list") or []),
        "missing_items": missing_items,
        "inventory_requirements": list(recipe.get("inventory_requirements") or []),
        "ingredient_adjustments": [
            item for item in recipe.get("inventory_requirements") or []
            if item.get("status") in {"Substitute", "Omit"}
        ],
        "serving_styles": list(recipe.get("serving_styles") or []),
        "serving_style": candidate.get("serving_style"),
        "build_provenance": provenance,
    }
