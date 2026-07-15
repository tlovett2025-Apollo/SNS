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
from sauce_profiles import get_sauce_profile


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
    sauce_profile = get_sauce_profile(sauce)
    selected_components = _unique([protein, *_clean(vegetable).split(" & "), foundation])
    available = _unique(list(available_items or []) + selected_components)
    equipment = _unique(list(available_equipment or []))
    sauce_items = (
        [item.name for item in sauce_profile.ingredients if not item.pantry_optional]
        if sauce_profile else _cuisine_requirements(cuisine)
    )
    required = _unique(selected_components + sauce_items + list(requested_items or []))
    available_keys = {_key(item) for item in available}
    needed = [item for item in required if _key(item) not in available_keys]
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
        if _method_is_eligible(method["cooking_method"], available, foundation, equipment)
    ]

    candidates = []
    for method in methods:
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
            "sauce": sauce,
            "protein": protein,
            "protein_state": protein_state,
            "vegetable": vegetable,
            "foundation": foundation,
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
            "available_equipment": equipment,
        })

        schedule = build_kitchen_lane_schedule(c)
        c["minutes"] = max((item.end_minute for item in schedule), default=0)
        c["active_minutes"] = sum(item.attention_minutes for item in schedule)
        c["passive_minutes"] = max(0, c["minutes"] - c["active_minutes"])
        c["effort_score"] = calculate_effort_score(c, schedule)
        c["inventory_requirements"] = [
            {
                "name": item.name,
                "quantity": item.quantity,
                "status": "Have" if _key(item.name) in available_keys else "Need",
                "required": not item.pantry_optional,
            }
            for item in (sauce_profile.ingredients if sauce_profile else [])
        ]
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
