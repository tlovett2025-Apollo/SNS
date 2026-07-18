from ingredient_profiles import get_ingredient_profile
from ko_behavior import default_form_for, resolve_behavior
from config import DB_PATH
from cooking_planner import (
    assess_time_feasibility,
    build_kitchen_lane_schedule,
    calculate_effort_score,
    generate_human_plan_items,
    generate_human_instruction_steps,
    generate_human_instructions,
    summarize_cooking_activities,
    summarize_kitchen_lanes,
)
from culinary_opportunities import discover_opportunities, serialize_opportunities
from sauce_profiles import SauceIngredient, get_sauce_profile
from recipe_validation import validate_recipe
from math import ceil, floor
import sqlite3


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ")


def _unique(items):
    out = []
    for item in items:
        item = _clean(item)
        if item and item not in out:
            out.append(item)
    return out


def _join(items):
    items = _unique(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return " & ".join(items)


def _inventory_has_ko(
    items, family_codes=(), physical_traits=(), relationship_traits=(),
    culinary_functions=(),
):
    family_codes = set(family_codes)
    physical_traits = set(physical_traits)
    relationship_traits = set(relationship_traits)
    culinary_functions = set(culinary_functions)
    for name in items:
        behavior = resolve_behavior(name, "ingredient", db_path=DB_PATH)
        if not behavior.primary_family:
            continue
        if family_codes & set(behavior.family_codes):
            return True
        if physical_traits & set(behavior.primary_family.physical_traits):
            return True
        if culinary_functions & set(behavior.primary_family.culinary_functions):
            return True
        all_relationships = {
            trait for family in [behavior.primary_family, *behavior.trait_families]
            for trait in family.relationship_traits
        }
        if relationship_traits & all_relationships:
            return True
    return False


def _ingredient_check(item, available, excluded, protein=""):
    """Resolve one requirement before a candidate is allowed into ranking."""
    available_by_key = {_key(name): name for name in available}
    excluded_keys = {_key(name) for name in excluded}
    name_key = _key(item.name)

    durable_substitutes = []
    with sqlite3.connect(DB_PATH) as con:
        durable_substitutes = [row[0] for row in con.execute(
            """SELECT substitute.name
               FROM ingredients original
               JOIN substitution_rules rule
                 ON rule.original_type='ingredient' AND rule.original_id=original.ingredient_id
               JOIN ingredients substitute
                 ON rule.substitute_type='ingredient' AND rule.substitute_id=substitute.ingredient_id
               WHERE lower(original.name)=lower(?)
               ORDER BY CASE rule.quality WHEN 'excellent' THEN 0 WHEN 'good' THEN 1 ELSE 2 END""",
            (item.name,),
        )]
    substitutes = _unique([*item.substitutes, *durable_substitutes])

    if name_key in available_by_key and name_key not in excluded_keys:
        status = "Have"
        resolved_name = available_by_key[name_key]
    else:
        resolved_name = next((
            available_by_key[_key(substitute)]
            for substitute in substitutes
            if _key(substitute) in available_by_key
            and _key(substitute) not in excluded_keys
        ), "")
        if resolved_name:
            status = "Substitute"
        elif (
            name_key in {_key("Water or broth"), _key("Broth or water")}
            and not (item.pantry_optional or item.can_omit)
        ):
            status = "Substitute"
            resolved_name = "Water"
        elif name_key == _key("Cold water") and not (item.pantry_optional or item.can_omit):
            status = "Have"
            resolved_name = "Cold water"
        elif (
            name_key == _key("Cooking oil or butter")
            and "fat-rendering" in set(
                getattr(resolve_behavior(protein, "protein", db_path=DB_PATH).primary_family, "physical_traits", ())
            )
        ):
            status = "Substitute"
            resolved_name = f"Rendered fat from {protein}"
        elif item.pantry_optional or item.can_omit:
            status = "Omit"
        elif name_key in excluded_keys:
            status = "Excluded"
        else:
            status = "Need"

    return {
        "name": item.name,
        "quantity": item.quantity,
        "status": status,
        "required": not (item.pantry_optional or item.can_omit),
        "resolved_name": resolved_name or None,
        "substitutions": substitutes,
        "omission_consequence": item.omission_consequence or None,
    }


def _component_check(name, available, excluded):
    name_key = _key(name)
    available_keys = {_key(item) for item in available}
    excluded_keys = {_key(item) for item in excluded}
    if name_key in excluded_keys:
        status = "Excluded"
    elif name_key in available_keys:
        status = "Have"
    else:
        status = "Need"
    return {
        "name": name,
        "quantity": "",
        "status": status,
        "required": True,
        "resolved_name": name if status == "Have" else None,
        "substitutions": [],
        "omission_consequence": None,
    }


def _effective_portions(servings, eater_profiles):
    """Translate appetite choices into planning portions without inventing people."""
    profiles = eater_profiles if isinstance(eater_profiles, dict) else {}
    if not profiles:
        return float(servings or 4)
    weights = {"light": 0.75, "standard": 1.0, "big": 1.5}
    total = sum(max(0, int(profiles.get(name) or 0)) * weight for name, weight in weights.items())
    return total or float(servings or 4)


def _quarter_pound_up(ounces):
    return ceil(max(0, ounces) / 4.0) / 4.0


def _quantity_plan(
    components, component_forms, inventory_lots, servings, eater_profiles,
    use_all_cans, component_roles=None,
):
    """Build practical cook amounts; package fractions stay estimates, never fake exact counts."""
    effective = _effective_portions(servings, eater_profiles)
    lots = {_key(item.get("name")): item for item in (inventory_lots or []) if isinstance(item, dict)}
    forms = {_key(name): _key(form) for name, form in (component_forms or {}).items()}
    roles = {_key(name): _key(role) for name, role in (component_roles or {}).items()}
    vegetable_count = max(1, sum(role == "vegetable" for role in roles.values()))
    plan = {}
    notes = []
    for name in components:
        key = _key(name)
        if not key:
            continue
        lot = lots.get(key, {})
        form = forms.get(key) or _key(lot.get("form"))
        unit = _key(lot.get("unit"))
        available = float(lot.get("quantity") or 0)
        behavior = resolve_behavior(name, "ingredient", form, db_path=DB_PATH)
        family = behavior.primary_family
        attributes = behavior.attributes or {}
        basis = attributes.get("quantity_basis") or (family.portion_basis if family else "flexible")
        try:
            amount = float(attributes.get("quantity_per_standard") or (family.portion_per_standard if family else 1.0))
        except (TypeError, ValueError):
            amount = family.portion_per_standard if family else 1.0
        quantity_label = attributes.get("quantity_label") or (family.portion_label if family else "")
        role = roles.get(key, "")
        # Supporting proteins flavor or stretch the main item. They must not
        # silently become another full entree merely because their KO normally
        # portions them as a main protein.
        amount *= .25 if role == "supporting" else .15 if role == "accent" else 1.0
        stretchable = bool(family and family.stretchable)
        is_canned = "canned" in form or unit in {"can", "cans"}
        if is_canned:
            planned = max(1, ceil(effective * (amount if basis == "cans" else .25)))
            if 0 < available < 0.5:
                display = f"{planned} can{'s' if planned != 1 else ''} needed; less than 1/2 can is on hand"
                notes.append(f"Less than half a can of {name} is not being counted as enough for this meal.")
            else:
                use = available if 0.5 <= available < planned else planned
                if use_all_cans and available > planned:
                    use = available
                    notes.append("Using all available cans will make the entire meal larger; adjust sauce and seasoning as needed.")
                display = f"{use:g} can{'s' if use != 1 else ''}"
            plan[key] = {"display": display, "unit": "can", "planned": planned, "available": available}
            if stretchable and available and available < planned:
                notes.append(
                    f"The {name} on hand appears short for the planned amount. Stretch it by distributing it through the selected vegetables or foundation."
                )
        elif basis == "pieces":
            pieces = max(1, ceil(effective * amount))
            label = quantity_label or "piece"
            plan[key] = {
                "display": f"{pieces} {label}{'' if pieces == 1 else 's'}",
                "planned": pieces, "available": available,
                "shortfall": max(0, pieces - available) if available else 0,
            }
            if unit in {"piece", "pieces"} and available and available < pieces:
                shortfall = pieces - available
                notes.append(
                    f"Only {available:g} {label}{'s are' if available != 1 else ' is'} recorded for {pieces} planned. "
                    f"Add {shortfall:g} more {label}{'' if shortfall == 1 else 's'} before making this meal."
                )
        elif basis == "dry_cups":
            cups = ceil(effective * amount * 4) / 4.0
            plan[key] = {"display": f"{cups:g} cup{'s' if cups != 1 else ''} dry"}
        elif basis == "prepared_cups":
            cups = ceil(effective * amount * 4) / 4.0
            plan[key] = {
                "display": f"about {cups:g} cup{'s' if cups != 1 else ''}",
                "planned": cups,
            }
        elif basis == "whole_count":
            pieces = max(1, ceil(effective * amount))
            label = quantity_label or "piece"
            plan[key] = {
                "display": f"{pieces} {label}{'' if pieces == 1 else 's'}",
                "planned": pieces, "available": available,
                "shortfall": max(0, pieces - available) if available else 0,
            }
        elif basis == "weight_oz":
            pounds = _quarter_pound_up(effective * amount)
            plan[key] = {"display": f"{pounds:g} lb", "planned": pounds, "available": available}
            available_pounds = available if unit in {"lb", "pound", "pounds"} else 0
            package_weight = float(lot.get("package_weight_oz") or 0)
            if unit in {"package", "packages"} and package_weight:
                available_pounds = available * package_weight / 16.0
            if available_pounds and available_pounds < pounds:
                notes.append(
                    f"About {available_pounds:g} lb of {name} is recorded for {pounds:g} lb planned. Stretch it through the selected vegetables or foundation."
                )
            elif unit in {"package", "packages"} and available and not package_weight:
                notes.append(
                    f"The {available:g}-package estimate for {name} is approximate because the original package weight is unknown."
                )
        elif role == "vegetable":
            # Produce varies in physical size, so cups prepared are more useful
            # and more honest than invented piece counts.
            cups = ceil(max(.5, effective * .5 / vegetable_count) * 4) / 4.0
            plan[key] = {"display": f"about {cups:g} cup{'s' if cups != 1 else ''} prepared"}
    # Many individually sensible vegetable portions can become an implausible
    # vessel load when selected together. Keep the whole meal to roughly
    # 1 1/2 prepared cups per planning portion, preserving at least 1/4 cup of
    # every vegetable the user explicitly chose.
    vegetable_keys = [
        key for key, role in roles.items()
        if role == "vegetable" and float((plan.get(key) or {}).get("planned") or 0) > 0
    ]
    total_vegetable_cups = sum(float(plan[key]["planned"]) for key in vegetable_keys)
    vegetable_budget = max(.25 * len(vegetable_keys), effective * 1.5)
    if vegetable_keys and total_vegetable_cups > vegetable_budget:
        target_quarters = max(len(vegetable_keys), floor(vegetable_budget * 4))
        scale = vegetable_budget / total_vegetable_cups
        exact_quarters = {
            key: float(plan[key]["planned"]) * scale * 4 for key in vegetable_keys
        }
        allocated = {key: max(1, floor(value)) for key, value in exact_quarters.items()}
        remaining = target_quarters - sum(allocated.values())
        for key in sorted(
            vegetable_keys,
            key=lambda item: exact_quarters[item] - floor(exact_quarters[item]),
            reverse=True,
        )[:max(0, remaining)]:
            allocated[key] += 1
        for key in vegetable_keys:
            cups = allocated[key] / 4.0
            plan[key]["planned"] = cups
            plan[key]["display"] = f"about {cups:g} cup{'s' if cups != 1 else ''}"

    note = " ".join(dict.fromkeys(notes))
    return effective, plan, note


def _score_strategy(strategy, energy, budget, time_limit):
    score = 100
    energy_order = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "": 2}
    budget_order = {"Pantry Only": 0, "Budget": 1, "Moderate": 2, "High": 3, "": 2}
    score -= max(0, strategy["energy_rank"] - energy_order.get(energy, 2)) * 12
    score -= max(0, strategy["budget_rank"] - budget_order.get(budget, 2)) * 10
    if time_limit and strategy["minutes"] > time_limit:
        score -= (strategy["minutes"] - time_limit) * 2
    return max(0, score)


def _ko_combination_fit(component_specs):
    """Score functions and sensory contrast, never conventional name pairings."""
    profiles = []
    for name, role, form in component_specs:
        behavior = resolve_behavior(name, role, form, db_path=DB_PATH)
        if behavior.primary_family:
            profiles.append(behavior.primary_family)
    functions = {value for profile in profiles for value in profile.culinary_functions}
    flavors = {value for profile in profiles for value in profile.flavor_domains}
    textures = {profile.texture_contribution for profile in profiles if profile.texture_contribution}
    colors = {profile.color_contribution for profile in profiles if profile.color_contribution}
    score = len(profiles) * 2
    reasons = []
    if "protein-anchor" in functions and "foundation" in functions:
        score += 6
        reasons.append("has a KO-defined protein and foundation")
    if "absorbs-sauce" in functions and functions & {"sauce-builder", "moisture-source", "supplies-liquid"}:
        score += 5
        reasons.append("has a foundation that can carry the meal's moisture and flavor")
    if flavors & {"rich", "savory", "umami"} and functions & {"brightness", "fresh-contrast", "balances-richness"}:
        score += 6
        reasons.append("balances savory richness with brightness or fresh contrast")
    if "browning-source" in functions and "moisture-source" in functions:
        score += 3
        reasons.append("can develop browning before a wetter component joins")
    if len(textures) >= 3:
        score += 4
        reasons.append("offers useful texture contrast")
    if len(colors) >= 2:
        score += 2
        reasons.append("offers visible color contrast")
    moisture_count = sum("moisture-source" in profile.culinary_functions for profile in profiles)
    if moisture_count > 2:
        score -= (moisture_count - 2) * 3
    family_codes = {profile.code for profile in profiles}
    if family_codes:
        placeholders = ",".join("?" for _ in family_codes)
        params = [*family_codes, *family_codes]
        with sqlite3.connect(DB_PATH) as con:
            durable = con.execute(
                f"""SELECT relationship_type, rule_text
                    FROM ko_relationship_rules relationship
                    JOIN ko_behavior_families source ON source.family_id=relationship.family_id
                    WHERE source.family_code IN ({placeholders})
                      AND relationship.target_family_code IN ({placeholders})
                      AND relationship.verified=1""",
                params,
            ).fetchall()
            compatibility = con.execute(
                f"""SELECT compatibility.rating, compatibility.reason
                    FROM compatibility_rules compatibility
                    JOIN ko_behavior_families source
                      ON compatibility.component_a_type='behavior_family'
                     AND source.family_id=compatibility.component_a_id
                    JOIN ko_behavior_families target
                      ON compatibility.component_b_type='behavior_family'
                     AND target.family_id=compatibility.component_b_id
                    WHERE source.family_code IN ({placeholders})
                      AND target.family_code IN ({placeholders})
                      AND compatibility.active=1""",
                params,
            ).fetchall()
        if durable:
            score += min(8, len(durable) * 2)
            reasons.extend(rule_text.removeprefix("[SNS seed] ") for _, rule_text in durable)
        if compatibility:
            rating_points = {"excellent": 4, "good": 2, "poor": -4}
            score += sum(rating_points.get(_key(rating), 0) for rating, _ in compatibility)
            reasons.extend(reason.removeprefix("[SNS seed] ") for _, reason in compatibility if reason)
    return score, _unique(reasons)


def _sauce_for_cuisine(cuisine):
    k = _key(cuisine)
    if "italian" in k:
        return "Italian tomato sauce"
    if "mexican" in k:
        return "Mexican taco sauce"
    if "comfort" in k or "american" in k:
        return "simple comfort pan sauce"
    if "mediterranean" in k:
        return "Mediterranean lemon herb sauce"
    if "bbq" in k:
        return "BBQ Sauce"
    if "cajun" in k:
        return "Cajun pan sauce"
    if "kid" in k:
        return "mild favorite sauce"
    if "chinese" in k:
        return "simple stir-fry sauce"
    if "indian" in k:
        return "Indian curry sauce"
    return "simple sauce"


def _cuisine_requirements(cuisine):
    """Prototype pantry requirements for optional cuisine intent."""
    k = _key(cuisine)
    if "chinese" in k:
        return ["Soy sauce", "Garlic"]
    if "italian" in k:
        return ["Tomato sauce", "Garlic"]
    if "mexican" in k:
        return ["Chili powder", "Cumin"]
    return []


def _first_soup_liquid(available):
    """Return the exact saved-kitchen name for the soup's cooking liquid."""
    for item in available:
        behavior = resolve_behavior(item, "ingredient", db_path=DB_PATH)
        functions = set(behavior.primary_family.culinary_functions) if behavior.primary_family else set()
        if "supplies-liquid" in functions:
            return item
    return "Broth or water"


def _soup_ingredients(available):
    """Minimal ingredients for a broth-based rustic soup.

    Soup owns this list; it must not inherit a skillet sauce merely because the
    two candidates share a cuisine label.
    """
    return [
        SauceIngredient(_first_soup_liquid(available), "3 cups, plus more if needed"),
        SauceIngredient("Garlic powder", "1/2 teaspoon"),
        SauceIngredient("Onion powder", "1/2 teaspoon"),
        SauceIngredient("Black pepper", "1/4 teaspoon"),
        SauceIngredient("Salt", "only after tasting, if needed", pantry_optional=True),
    ]


def _method_is_eligible(method, available, foundation, equipment):
    """Reject cooking methods that the current kitchen cannot support.

    This is intentionally conservative. A method must be valid before ranking;
    scoring never rescues a meal form that should not have existed.
    """
    equipment_keys = {_key(item) for item in equipment}

    if method == "skillet":
        return True
    if method == "soup":
        # Water is a legitimate soup liquid, and broth can be an explicit
        # shopping need. Ingredient KOs—not current broth ownership—decide
        # whether the selected components have a trained soup route.
        return True
    if method == "braise":
        return _inventory_has_ko(
            available, physical_traits=("collagen-rich",), relationship_traits=("wet-cook",)
        )
    if method == "oven_braise":
        if equipment_keys and not any("oven" in item for item in equipment_keys):
            return False
        return _inventory_has_ko(
            available, physical_traits=("collagen-rich",), relationship_traits=("wet-cook",)
        )
    if method == "casserole":
        if equipment_keys and not any("oven" in item for item in equipment_keys):
            return False
        return bool(foundation) or _inventory_has_ko(
            available, culinary_functions=("sauce-builder", "thickens", "adds-richness")
        )
    if method == "handheld":
        return _inventory_has_ko(available, family_codes=("bread_wrap",))
    if method == "grill":
        return any("grill" in item for item in equipment_keys)
    if method == "cold_meal":
        return _inventory_has_ko(
            available, physical_traits=("ready-to-eat",),
            relationship_traits=("no-cook-default", "assembly-foundation"),
        )
    return False


def _serving_styles(method):
    """Return presentation choices independently from cooking method."""
    if method == "soup":
        return ["bowl", "cup"]
    if method in {"braise", "oven_braise"}:
        return ["plate", "bowl"]
    if method == "handheld":
        return ["handheld", "plate"]
    if method == "cold_meal":
        return ["plate", "bowl", "handheld"]
    return ["plate", "bowl"]


def _experience_overlays(cooking_for_kids=False, kid_theme=""):
    if not cooking_for_kids:
        return []
    return [{
        "type": "kid_adventure",
        "theme": _clean(kid_theme) or "surprise_me",
        "same_meal": True,
        "include_fun_facts": True,
        "include_conversation_prompts": True,
    }]


def generate_candidates(
    protein_name="",
    vegetable_name="",
    foundation_name="",
    cuisine_name="",
    energy_level="",
    budget_level="",
    time_minutes=30,
    servings=4,
    max_results=10,
    vegetable_names=None,
    protein_state="Fresh Raw",
    available_items=None,
    requested_items=None,
    available_equipment=None,
    excluded_items=None,
    planned_purchase_items=None,
    requested_method="",
    selected_extras=None,
    component_forms=None,
    meal_structure="integrated",
    inventory_lots=None,
    eater_profiles=None,
    use_all_cans=False,
    cooking_for_kids=False,
    kid_theme="",
    protein_names=None,
    protein_states=None,
    protein_roles=None,
):
    proteins = _unique(list(protein_names or []) or [_clean(protein_name)])
    protein = proteins[0] if proteins else ""
    protein_states = dict(protein_states or {})
    protein_roles = dict(protein_roles or {})
    protein_state = _clean(protein_states.get(protein) or protein_state) or "Fresh Raw"

    if vegetable_names:
        vegetable = _join(vegetable_names)
    else:
        vegetable = _clean(vegetable_name)

    foundation = _clean(foundation_name)
    cuisine = _clean(cuisine_name) or "Comfort Food"
    sauce = _sauce_for_cuisine(cuisine)
    selected_components = _unique([*proteins, *_clean(vegetable).split(" & "), foundation])
    extras = _unique(list(selected_extras or []))
    component_forms = dict(component_forms or {})
    for name in _clean(vegetable).split(" & "):
        if _clean(name) and not _clean(component_forms.get(name)):
            component_forms[name] = default_form_for(name, "vegetable", DB_PATH)
    if foundation and not _clean(component_forms.get(foundation)):
        component_forms[foundation] = default_form_for(foundation, "foundation", DB_PATH)
    planned_purchase_keys = {_key(item) for item in (planned_purchase_items or [])}
    available = _unique(list(available_items or []) + [
        item for item in selected_components if _key(item) not in planned_purchase_keys
    ])
    # Eligibility is about whether the finished meal has the component, while
    # ingredient status is about whether the household owns it today.
    method_resources = _unique(available + selected_components + extras)
    equipment = _unique(list(available_equipment or []))
    excluded = _unique(list(excluded_items or []))
    try:
        time_limit = int(time_minutes)
    except Exception:
        time_limit = 30
    try:
        servings = int(servings)
    except Exception:
        servings = 4

    base = _join([protein, vegetable]) or protein or vegetable or "Pantry"
    methods = [
        {"strategy": "skillet", "cooking_method": "skillet", "label": "Skillet", "title": f"{cuisine} {base} Skillet", "minutes": 25, "energy": "Low", "energy_rank": 1, "budget": "Budget", "budget_rank": 1, "why": "one pan, flexible texture"},
        {"strategy": "casserole", "cooking_method": "casserole", "label": "Casserole", "title": f"{cuisine} {base} {foundation} Casserole" if foundation else f"{cuisine} {base} Casserole", "minutes": 40, "energy": "Medium", "energy_rank": 2, "budget": "Budget", "budget_rank": 1, "why": "family-style and good for leftovers"},
        {"strategy": "soup", "cooking_method": "soup", "label": "Soup", "title": f"{cuisine} {base} Soup", "minutes": 30, "energy": "Low", "energy_rank": 1, "budget": "Budget", "budget_rank": 1, "why": "soft, stretchable, and forgiving"},
        {"strategy": "handheld", "cooking_method": "handheld", "label": "Handheld", "title": f"{cuisine} {base} Wrap or Sandwich", "minutes": 18, "energy": "Low", "energy_rank": 1, "budget": "Budget", "budget_rank": 1, "why": "portable and easy to serve"},
        {"strategy": "grill", "cooking_method": "grill", "label": "Grill", "title": f"Grilled {cuisine} {base}", "minutes": 25, "energy": "Medium", "energy_rank": 2, "budget": "Moderate", "budget_rank": 2, "why": "direct high-heat cooking with simple sides"},
        {"strategy": "cold_meal", "cooking_method": "cold_meal", "label": "Cold Meal", "title": f"Cold {cuisine} {base} Meal", "minutes": 12, "energy": "Very Low", "energy_rank": 0, "budget": "Budget", "budget_rank": 1, "why": "no-cook or low-cook assembly"},
        {"strategy": "braise", "cooking_method": "braise", "label": "Stovetop Braise", "title": f"{cuisine} {base} Stovetop Braise", "minutes": 120, "energy": "Low", "energy_rank": 1, "budget": "Moderate", "budget_rank": 2, "why": "a patient covered cook makes a collagen-rich cut tender"},
        {"strategy": "oven_braise", "cooking_method": "oven_braise", "label": "Oven Braise", "title": f"{cuisine} {base} Oven Braise", "minutes": 150, "energy": "Low", "energy_rank": 1, "budget": "Moderate", "budget_rank": 2, "why": "a covered moderate oven makes a collagen-rich cut tender"},
    ]
    requested = _clean(requested_method)
    requested_methods = {requested} if requested else set()
    # The public builder asks for a broad Stovetop environment. A
    # collagen-rich protein turns it into a covered braise instead of being
    # forced through quick-skillet grammar.
    if requested == "skillet":
        requested_methods.add("braise")
    if requested == "casserole":
        requested_methods.add("oven_braise")
    methods = [
        method for method in methods
        if _method_is_eligible(method["cooking_method"], method_resources, foundation, equipment)
        and (not requested_methods or method["cooking_method"] in requested_methods)
    ]

    candidates = []
    for method in methods:
        # A classified ingredient may only enter a cooking environment for
        # which its KO family has an explicit method. Unclassified legacy KOs
        # remain visible for migration; classified-but-incompatible ones do
        # not fall through to invented generic cooking language.
        environment = method["cooking_method"]
        behavior_components = [
            *[(name, "protein", _clean(protein_states.get(name)) or (protein_state if name == protein else "Fresh Raw")) for name in proteins],
            *[(name, "vegetable", _clean(component_forms.get(name)) or "Fresh") for name in _clean(vegetable).split(" & ") if _clean(name)],
            *([(foundation, "foundation", _clean(component_forms.get(foundation)) or "")] if foundation else []),
        ]
        incompatible = False
        for component_name, component_role, component_form in behavior_components:
            behavior = resolve_behavior(component_name, component_role, component_form, environment, DB_PATH)
            if behavior.primary_family and behavior.method is None:
                incompatible = True
                break
        if incompatible:
            continue
        is_soup = method["cooking_method"] == "soup"
        is_braise = method["cooking_method"] in {"braise", "oven_braise"}
        is_grill = method["cooking_method"] == "grill"
        method_sauce = (
            "rustic broth soup" if is_soup
            else "simple sauce" if is_grill
            else "handheld spread or sauce" if method["cooking_method"] == "handheld"
            else sauce
        )
        method_ingredients = (
            _soup_ingredients(method_resources)
            if is_soup
            else (
                get_sauce_profile(method_sauce).ingredients
                if get_sauce_profile(method_sauce)
                else (_soup_ingredients(method_resources) if is_braise else [])
            )
        )
        fallback_requirements = (
            [] if method["cooking_method"] == "handheld"
            else _cuisine_requirements(cuisine) if not method_ingredients else []
        )
        requested_names = [*fallback_requirements, *extras, *(requested_items or [])]
        known_requirement_keys = {_key(item.name) for item in method_ingredients}
        requested_requirements = [
            SauceIngredient(_clean(name), "")
            for name in requested_names
            if _clean(name) and _key(name) not in known_requirement_keys
        ]
        component_checks = [
            _component_check(item, available, excluded)
            for item in selected_components
        ]
        requirement_checks = [
            _ingredient_check(item, available, excluded, protein)
            for item in [*method_ingredients, *requested_requirements]
        ]
        consolidated_checks = []
        effective_indexes = {}
        for check in requirement_checks:
            effective_key = _key(check.get("resolved_name") or check.get("name"))
            if effective_key in effective_indexes:
                existing = consolidated_checks[effective_indexes[effective_key]]
                if not _clean(existing.get("quantity")) and _clean(check.get("quantity")):
                    existing["quantity"] = check["quantity"]
                existing["required"] = bool(existing.get("required") or check.get("required"))
                continue
            effective_indexes[effective_key] = len(consolidated_checks)
            consolidated_checks.append(check)
        requirement_checks = consolidated_checks
        ingredient_checks = component_checks + requirement_checks
        for check in ingredient_checks:
            check["planned_purchase"] = _key(check.get("name")) in planned_purchase_keys
            # Selecting an extra in Build My Meal is an explicit request to use
            # it, even when that ingredient is optional in the generic profile.
            if _key(check.get("name")) in {_key(item) for item in extras}:
                check["required"] = True
                if check["status"] == "Omit":
                    check.update(status="Need", omission_consequence=None)

        # A structural ingredient and a supporting seasoning may express the
        # same flavor identity.  KO attributes—not ingredient-name branches—
        # decide when the second expression is redundant.
        selected_identities = {
            resolve_behavior(
                item, "ingredient", component_forms.get(item, ""), db_path=DB_PATH
            ).attributes.get("flavor_identity")
            for item in selected_components
        }
        selected_identities.discard(None)
        for check in requirement_checks:
            requirement_identity = resolve_behavior(
                check.get("name"), "ingredient", db_path=DB_PATH
            ).attributes.get("flavor_identity")
            if requirement_identity and requirement_identity in selected_identities:
                check.update(status="Omit", required=False, resolved_name=None,
                             omission_consequence=(
                                 "A selected ingredient already provides this flavor identity; "
                                 "omit the duplicate seasoning unless you deliberately want it stronger."
                             ))

        # Culinary validity and household safety are gates, not score penalties.
        # Excluded ingredients must never reach ranking. Missing ingredients
        # remain explicit Needs so the UI can offer trained substitutes or a
        # short shopping resolution instead of silently assuming possession.
        if any(item["status"] == "Excluded" for item in component_checks):
            continue
        if any(item["status"] == "Excluded" for item in requirement_checks):
            continue

        needed = [
            item["name"] for item in ingredient_checks
            if item["status"] == "Need" and item["required"]
        ]
        score = _score_strategy(method, energy_level, budget_level, time_limit)
        combination_score, combination_reasons = _ko_combination_fit(behavior_components)
        score += combination_score
        c = dict(method)
        c["serving_styles"] = _serving_styles(method["cooking_method"])
        c["serving_style"] = c["serving_styles"][0]
        c["experience_overlays"] = _experience_overlays(cooking_for_kids, kid_theme)
        c["combination_reasons"] = combination_reasons
        component_roles = {
            **{name: _clean(protein_roles.get(name)) or ("main" if name == protein else "supporting") for name in proteins},
            **{name: "vegetable" for name in _clean(vegetable).split(" & ") if _clean(name)},
            **({foundation: "foundation"} if foundation else {}),
        }
        effective, quantity_plan, quantity_note = _quantity_plan(
            selected_components, component_forms, inventory_lots, servings,
            eater_profiles, use_all_cans, component_roles,
        )
        primary_quantity = quantity_plan.get(_key(protein), {})
        if (
            _clean(meal_structure) == "composed_plate"
            and float(primary_quantity.get("shortfall") or 0) > 0
            and _key(protein) not in planned_purchase_keys
        ):
            # A composed plate promises a discrete entree portion to each
            # diner. Inventory-only idea generation must honor that promise;
            # Build My Meal may satisfy it through the generated grocery list.
            continue
        c["effective_portions"] = effective
        c["quantity_plan"] = quantity_plan
        c["quantity_note"] = quantity_note
        c["inventory_lots"] = list(inventory_lots or [])
        for check in component_checks:
            planned = quantity_plan.get(_key(check.get("name")), {})
            shortfall = float(planned.get("shortfall") or 0)
            if shortfall > 0:
                check.update(
                    status="Short", required=True, quantity_shortfall=shortfall,
                    planned_quantity=planned.get("planned"), available_quantity=planned.get("available"),
                )
                needed.append(f"{check['name']} ({shortfall:g} more)")

        protein_profiles = [
            (name, get_ingredient_profile(name, "protein"), _clean(protein_states.get(name)) or (protein_state if name == protein else "Fresh Raw"))
            for name in proteins
        ]
        protein_profile = protein_profiles[0][1] if protein_profiles else None
        vegetable_profiles = [
            get_ingredient_profile(v, "vegetable")
            for v in vegetable.split(" & ")
            if _clean(v)
        ]
        foundation_profile = get_ingredient_profile(foundation, "foundation") if foundation else None

        active_minutes = 0
        for _protein_name, current_profile, current_state in protein_profiles:
            selected_state = current_profile.get_state(current_state)
            if selected_state:
                active_minutes += selected_state.prep_minutes + selected_state.active_minutes
            else:
                active_minutes += current_profile.total_active_minutes
        for vegetable_profile in vegetable_profiles:
            active_minutes += vegetable_profile.total_active_minutes
        if foundation_profile:
            active_minutes += foundation_profile.total_active_minutes

        passive_minutes = 0
        for _protein_name, current_profile, current_state in protein_profiles:
            selected_state = current_profile.get_state(current_state)
            if selected_state:
                passive_minutes = max(passive_minutes, selected_state.passive_minutes + current_profile.rest_minutes)
            else:
                passive_minutes = max(passive_minutes, current_profile.total_passive_minutes)
        for vegetable_profile in vegetable_profiles:
            passive_minutes = max(passive_minutes, vegetable_profile.total_passive_minutes)
        if foundation_profile:
            passive_minutes = max(passive_minutes, foundation_profile.total_passive_minutes)

        attention_score = 0
        for _protein_name, current_profile, current_state in protein_profiles:
            selected_state = current_profile.get_state(current_state)
            attention_score = max(
                attention_score,
                selected_state.attention_score if selected_state else current_profile.attention_score,
            )
        for vegetable_profile in vegetable_profiles:
            attention_score = max(attention_score, vegetable_profile.attention_score)
        if foundation_profile:
            attention_score = max(attention_score, foundation_profile.attention_score)

        c.update({
            "score": score,
            "sauce": method_sauce,
            "protein": protein,
            "protein_state": protein_state,
            "proteins": [
                {
                    "name": name,
                    "state": _clean(protein_states.get(name)) or (protein_state if name == protein else "Fresh Raw"),
                    "role": _clean(protein_roles.get(name)) or ("main" if name == protein else "supporting"),
                }
                for name in proteins
            ],
            "vegetable": vegetable,
            "foundation": foundation,
            "selected_extras": extras,
            "component_forms": component_forms,
            "meal_structure": _clean(meal_structure) or "integrated",
            "cuisine": cuisine,
            "servings": servings,
            "active_minutes": active_minutes,
            "passive_minutes": passive_minutes,
            "minutes": active_minutes + passive_minutes,
            "attention_score": attention_score,
            "effort_score": 0,
            "user_energy": energy_level,
            "user_budget": budget_level,
            "max_time_minutes": time_limit,
            "inventory_have": available,
            "inventory_need": needed,
            "inventory_requirements": ingredient_checks,
            "available_equipment": equipment,
        })
        if is_soup:
            liquid_requirement = next((
                item for item in requirement_checks
                if _key(item.get("name")) == _key(method_ingredients[0].name)
            ), {})
            c["soup_liquid"] = _clean(
                liquid_requirement.get("resolved_name")
                if liquid_requirement.get("status") == "Substitute"
                else liquid_requirement.get("name")
            ) or method_ingredients[0].name
            c["soup_liquid_quantity"] = method_ingredients[0].quantity

        schedule = build_kitchen_lane_schedule(c)
        c["minutes"] = max((item.end_minute for item in schedule), default=0)
        c["active_minutes"] = sum(item.attention_minutes for item in schedule)
        c["passive_minutes"] = max(0, c["minutes"] - c["active_minutes"])
        c["effort_score"] = calculate_effort_score(c, schedule)
        active_ratio = c["active_minutes"] / c["minutes"] if c["minutes"] else 1
        c["energy"] = (
            "Low" if c["active_minutes"] <= 30 and active_ratio <= .35
            else "Medium" if c["active_minutes"] <= 40 and active_ratio <= .65
            else "High"
        )
        feasibility = assess_time_feasibility(c, time_limit)
        c.update(feasibility)
        if not c["time_feasible"]:
            c["score"] = max(0, c["score"] - c["time_shortfall_minutes"] * 5)
        c["opportunities"] = serialize_opportunities(discover_opportunities(c))
        plan_items = generate_human_plan_items(c)
        c["recipe_validation"] = validate_recipe(c, plan_items)
        if c["recipe_validation"]["errors"]:
            # Candidate generation fails closed. A meal that cannot survive the
            # whole-recipe contract is never offered and therefore can never
            # reach Phase 3.
            continue
        candidates.append(c)

    candidates.sort(key=lambda x: (x["time_feasible"], x["score"]), reverse=True)
    return candidates[:max_results]


def build_recipe_from_candidate(candidate):
    plan_items = generate_human_plan_items(candidate)
    instructions = [item["text"] for item in plan_items]
    action_steps = [item["text"] for item in plan_items if item["kind"] == "action"]
    activity_debug = summarize_cooking_activities(candidate)
    lane_debug = summarize_kitchen_lanes(candidate)
    validation = validate_recipe(candidate, plan_items)
    if validation["errors"]:
        raise ValueError("Recipe validation failed: " + " ".join(validation["errors"]))

    return {
        "name": candidate.get("title", "Generated Meal"),
        "instructions": instructions,
        "action_steps": action_steps,
        "plan_items": plan_items,
        "activity_debug": activity_debug,
        "lane_debug": lane_debug,
        "opportunities": list(candidate.get("opportunities") or []),
        "grocery_list": list(candidate.get("inventory_need") or []),
        "inventory_requirements": list(candidate.get("inventory_requirements") or []),
        "selected_rice_equipment": candidate.get("selected_rice_equipment", ""),
        "servings": candidate.get("servings", 4),
        "cooking_method": candidate.get("cooking_method", candidate.get("strategy", "")),
        "serving_styles": list(candidate.get("serving_styles") or []),
        "experience_overlays": list(candidate.get("experience_overlays") or []),
        "quantity_note": candidate.get("quantity_note") or "",
        "validation": validation,
        "summary": f"{candidate.get('label')} · {candidate.get('energy')} energy · {candidate.get('budget')} · {candidate.get('minutes')} min · serves {candidate.get('servings', 4)}",
    }


def build_simple_meal(
    protein_name,
    vegetable_name,
    foundation_name,
    sauce_name="",
    flavor_name="",
    meal_template="",
):
    return build_recipe_from_candidate(
        generate_candidates(
            protein_name,
            vegetable_name,
            foundation_name,
            flavor_name or "Comfort Food",
            "Low",
            "Budget",
            30,
            4,
            1,
        )[0]
    )
