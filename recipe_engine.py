from ingredient_profiles import get_ingredient_profile
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


def _contains_any(items, terms):
    keys = {_key(item) for item in items}
    return any(any(term in item for term in terms) for item in keys)


def _ingredient_check(item, available, excluded, protein=""):
    """Resolve one requirement before a candidate is allowed into ranking."""
    available_by_key = {_key(name): name for name in available}
    excluded_keys = {_key(name) for name in excluded}
    name_key = _key(item.name)

    if name_key in available_by_key and name_key not in excluded_keys:
        status = "Have"
        resolved_name = available_by_key[name_key]
    else:
        resolved_name = next((
            available_by_key[_key(substitute)]
            for substitute in item.substitutes
            if _key(substitute) in available_by_key
            and _key(substitute) not in excluded_keys
        ), "")
        if resolved_name:
            status = "Substitute"
        elif name_key == _key("Cooking oil or butter") and "ground" in _key(protein):
            status = "Substitute"
            resolved_name = "Rendered fat from the ground beef"
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
        "substitutions": list(item.substitutes),
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


def _score_strategy(strategy, energy, budget, time_limit):
    score = 100
    energy_order = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "": 2}
    budget_order = {"Pantry Only": 0, "Budget": 1, "Moderate": 2, "High": 3, "": 2}
    score -= max(0, strategy["energy_rank"] - energy_order.get(energy, 2)) * 12
    score -= max(0, strategy["budget_rank"] - budget_order.get(budget, 2)) * 10
    if time_limit and strategy["minutes"] > time_limit:
        score -= (strategy["minutes"] - time_limit) * 2
    return max(0, score)


def _sauce_for_cuisine(cuisine):
    k = _key(cuisine)
    if "italian" in k:
        return "Tomato Sauce or Cream Sauce"
    if "mexican" in k:
        return "Taco Sauce"
    if "comfort" in k or "american" in k:
        return "simple comfort pan sauce"
    if "mediterranean" in k:
        return "Lemon Herb Sauce"
    if "bbq" in k:
        return "BBQ Sauce"
    if "cajun" in k:
        return "Cajun pan sauce"
    if "kid" in k:
        return "Favorite dip"
    if "chinese" in k:
        return "simple stir-fry sauce"
    if "indian" in k:
        return "curry sauce"
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
    terms = ("broth", "stock", "bouillon", "soup base", "consomme")
    return next(
        (item for item in available if any(term in _key(item) for term in terms)),
        "Broth or water",
    )


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
        has_liquid_path = _contains_any(
            available,
            ("broth", "stock", "bouillon", "soup base", "cream of", "consomme"),
        )
        inherently_stewable = _contains_any(available, ("stew meat",))
        return has_liquid_path or inherently_stewable
    if method == "casserole":
        return bool(foundation) or _contains_any(
            available,
            ("cream of", "sauce", "cheese", "egg", "breadcrumbs", "cracker"),
        )
    if method == "handheld":
        return _contains_any(
            available,
            ("bread", "bun", "roll", "tortilla", "wrap", "pita", "naan", "flatbread"),
        )
    if method == "grill":
        return any("grill" in item for item in equipment_keys)
    if method == "cold_meal":
        return _contains_any(
            available,
            ("cooked", "leftover", "canned", "bread", "tortilla", "lettuce", "greens", "cheese"),
        )
    return False


def _serving_styles(method):
    """Return presentation choices independently from cooking method."""
    if method == "soup":
        return ["bowl", "cup"]
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
    cooking_for_kids=False,
    kid_theme="",
):
    protein = _clean(protein_name)
    protein_state = _clean(protein_state) or "Fresh Raw"

    if vegetable_names:
        vegetable = _join(vegetable_names)
    else:
        vegetable = _clean(vegetable_name)

    foundation = _clean(foundation_name)
    cuisine = _clean(cuisine_name) or "Comfort Food"
    sauce = _sauce_for_cuisine(cuisine)
    selected_components = _unique([protein, *_clean(vegetable).split(" & "), foundation])
    extras = _unique(list(selected_extras or []))
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
    ]
    methods = [
        method for method in methods
        if _method_is_eligible(method["cooking_method"], method_resources, foundation, equipment)
        and (not _clean(requested_method) or method["cooking_method"] == _clean(requested_method))
    ]

    candidates = []
    for method in methods:
        is_soup = method["cooking_method"] == "soup"
        method_sauce = "rustic broth soup" if is_soup else sauce
        method_ingredients = (
            _soup_ingredients(method_resources)
            if is_soup
            else (
                get_sauce_profile(method_sauce).ingredients
                if get_sauce_profile(method_sauce)
                else []
            )
        )
        fallback_requirements = (
            _cuisine_requirements(cuisine) if not method_ingredients else []
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
        ingredient_checks = component_checks + requirement_checks

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
        c = dict(method)
        c["serving_styles"] = _serving_styles(method["cooking_method"])
        c["serving_style"] = c["serving_styles"][0]
        c["experience_overlays"] = _experience_overlays(cooking_for_kids, kid_theme)

        protein_profile = get_ingredient_profile(protein, "protein") if protein else None
        vegetable_profiles = [
            get_ingredient_profile(v, "vegetable")
            for v in vegetable.split(" & ")
            if _clean(v)
        ]
        foundation_profile = get_ingredient_profile(foundation, "foundation") if foundation else None

        active_minutes = 0
        if protein_profile:
            selected_state = protein_profile.get_state(protein_state)
            if selected_state:
                active_minutes += selected_state.prep_minutes + selected_state.active_minutes
            else:
                active_minutes += protein_profile.total_active_minutes
        for vegetable_profile in vegetable_profiles:
            active_minutes += vegetable_profile.total_active_minutes
        if foundation_profile:
            active_minutes += foundation_profile.total_active_minutes

        passive_minutes = 0
        if protein_profile:
            selected_state = protein_profile.get_state(protein_state)
            if selected_state:
                passive_minutes = max(passive_minutes, selected_state.passive_minutes + protein_profile.rest_minutes)
            else:
                passive_minutes = max(passive_minutes, protein_profile.total_passive_minutes)
        for vegetable_profile in vegetable_profiles:
            passive_minutes = max(passive_minutes, vegetable_profile.total_passive_minutes)
        if foundation_profile:
            passive_minutes = max(passive_minutes, foundation_profile.total_passive_minutes)

        attention_score = 0
        if protein_profile:
            selected_state = protein_profile.get_state(protein_state)
            attention_score = max(
                attention_score,
                selected_state.attention_score if selected_state else protein_profile.attention_score,
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
            "vegetable": vegetable,
            "foundation": foundation,
            "selected_extras": extras,
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
            c["soup_liquid"] = method_ingredients[0].name
            c["soup_liquid_quantity"] = method_ingredients[0].quantity

        schedule = build_kitchen_lane_schedule(c)
        c["minutes"] = max((item.end_minute for item in schedule), default=0)
        c["active_minutes"] = sum(item.attention_minutes for item in schedule)
        c["passive_minutes"] = max(0, c["minutes"] - c["active_minutes"])
        c["effort_score"] = calculate_effort_score(c, schedule)
        feasibility = assess_time_feasibility(c, time_limit)
        c.update(feasibility)
        if not c["time_feasible"]:
            c["score"] = max(0, c["score"] - c["time_shortfall_minutes"] * 5)
        c["opportunities"] = serialize_opportunities(discover_opportunities(c))
        candidates.append(c)

    candidates.sort(key=lambda x: (x["time_feasible"], x["score"]), reverse=True)
    return candidates[:max_results]


def build_recipe_from_candidate(candidate):
    plan_items = generate_human_plan_items(candidate)
    instructions = [item["text"] for item in plan_items]
    action_steps = [item["text"] for item in plan_items if item["kind"] == "action"]
    activity_debug = summarize_cooking_activities(candidate)
    lane_debug = summarize_kitchen_lanes(candidate)

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
