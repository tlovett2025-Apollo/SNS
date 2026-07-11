from ingredient_profiles import get_ingredient_profile
from cooking_planner import (
    build_kitchen_lane_schedule,
    generate_human_instructions,
    summarize_cooking_activities,
    summarize_kitchen_lanes,
)
from culinary_opportunities import discover_opportunities, serialize_opportunities

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
        return "Gravy or Cream Sauce"
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
):
    protein = _clean(protein_name)
    protein_state = _clean(protein_state) or "Fresh Raw"

    if vegetable_names:
        vegetable = _join(vegetable_names)
    else:
        vegetable = _clean(vegetable_name)
    
    foundation = _clean(foundation_name)
    cuisine = _clean(cuisine_name) or "Comfort Food"
    try:
        time_limit = int(time_minutes)
    except Exception:
        time_limit = 30
    try:
        servings = int(servings)
    except Exception:
        servings = 4

    base = _join([protein, vegetable]) or protein or vegetable or "Pantry"
    sauce = _sauce_for_cuisine(cuisine)
    strategies = [
        {"strategy": "quick_bowl", "label": "Quick Bowl", "title": f"{cuisine} {base} Bowl" if foundation else f"{cuisine} {base} Dinner Bowl", "minutes": 15, "energy": "Very Low", "energy_rank": 0, "budget": "Budget", "budget_rank": 1, "why": "fastest low-energy assembly"},
        {"strategy": "skillet", "label": "Skillet", "title": f"{cuisine} {base} Skillet", "minutes": 25, "energy": "Low", "energy_rank": 1, "budget": "Budget", "budget_rank": 1, "why": "one pan, flexible texture"},
        {"strategy": "casserole", "label": "Casserole", "title": f"{cuisine} {base} {foundation} Casserole" if foundation else f"{cuisine} {base} Casserole", "minutes": 40, "energy": "Medium", "energy_rank": 2, "budget": "Budget", "budget_rank": 1, "why": "family-style and good for leftovers"},
        {"strategy": "soup", "label": "Soup", "title": f"{cuisine} {base} Soup", "minutes": 30, "energy": "Low", "energy_rank": 1, "budget": "Budget", "budget_rank": 1, "why": "soft, stretchable, and forgiving"},
        {"strategy": "plate", "label": "Plate", "title": f"{cuisine} {base} Plate", "minutes": 20, "energy": "Low", "energy_rank": 1, "budget": "Moderate", "budget_rank": 2, "why": "simple meat/veg/foundation serving"},
        {"strategy": "handheld", "label": "Handheld", "title": f"{cuisine} {base} Wrap or Sandwich", "minutes": 18, "energy": "Low", "energy_rank": 1, "budget": "Budget", "budget_rank": 1, "why": "good when standing/eating energy is limited"},
        {"strategy": "kid_adventure", "label": "Kid Adventure", "title": f"{base} Adventure Plate", "minutes": 15, "energy": "Very Low", "energy_rank": 0, "budget": "Budget", "budget_rank": 1, "why": "playful plating and familiar components"},
    ]
    candidates = []
    for s in strategies:
        score = _score_strategy(s, energy_level, budget_level, time_limit)
        if cuisine == "Kid Friendly" and s["strategy"] == "kid_adventure":
            score += 18
        if not foundation and s["strategy"] in ["quick_bowl", "casserole"]:
            score -= 8

        c = dict(s)


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

        effort_score = protein_profile.effort_score() if protein_profile else 0

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
            "effort_score": effort_score,
        })

        schedule = build_kitchen_lane_schedule(c)
        c["minutes"] = max((item.end_minute for item in schedule), default=0)
        c["opportunities"] = serialize_opportunities(discover_opportunities(c))
        candidates.append(c)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:max_results]


def build_recipe_from_candidate(candidate):
    protein = candidate.get("protein", "")
    vegetable = candidate.get("vegetable", "")
    foundation = candidate.get("foundation", "")
    instructions = generate_human_instructions(candidate)
    activity_debug = summarize_cooking_activities(candidate)
    lane_debug = summarize_kitchen_lanes(candidate)

    return {
        "name": candidate.get("title", "Generated Meal"),
        "instructions": instructions.split("\n"),
        "activity_debug": activity_debug,
        "lane_debug": lane_debug,
        "opportunities": list(candidate.get("opportunities") or []),
        "grocery_list": _unique([protein, vegetable, foundation]),
        "servings": candidate.get("servings", 4),
        "summary": f"{candidate.get('label')} · {candidate.get('energy')} energy · {candidate.get('budget')} · {candidate.get('minutes')} min · serves {candidate.get('servings', 4)}"
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