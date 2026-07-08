from cooking_planner import build_plan_summary, generate_human_instructions


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ")


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [_clean(v) for v in value if _clean(v)]
    text = _clean(value)
    if not text:
        return []
    return [part.strip() for part in text.replace(" & ", ",").split(",") if part.strip()]


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
    if len(items) == 2:
        return " & ".join(items)
    return ", ".join(items[:-1]) + f" & {items[-1]}"


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


def _energy_rank(value):
    return {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "": 2}.get(value, 2)


def _budget_rank(value):
    return {"Pantry Only": 0, "Budget": 1, "Moderate": 2, "High": 3, "": 2}.get(value, 2)


def _score_candidate(candidate, requested_energy, requested_budget, requested_time):
    plan = build_plan_summary(candidate)
    score = 100

    # Score against real plan behavior, not just the strategy label.
    if requested_time and plan["total_minutes"] > requested_time:
        score -= (plan["total_minutes"] - requested_time) * 2

    if requested_energy == "Very Low":
        score -= max(0, plan["active_minutes"] - 12) * 3
        score -= max(0, plan["attention_score"] - 4) * 6
    elif requested_energy == "Low":
        score -= max(0, plan["active_minutes"] - 22) * 2
        score -= max(0, plan["attention_score"] - 6) * 4

    # Keep the old strategy preference as a mild signal only.
    score -= max(0, candidate["energy_rank"] - _energy_rank(requested_energy)) * 8
    score -= max(0, candidate["budget_rank"] - _budget_rank(requested_budget)) * 8

    if candidate.get("strategy") == "kid_adventure" and candidate.get("cuisine") == "Kid Friendly":
        score += 15

    return max(0, round(score)), plan


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
):
    protein = _clean(protein_name)
    vegetables = _as_list(vegetable_names if vegetable_names is not None else vegetable_name)
    vegetable = _join(vegetables)
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

    base = _join([protein] + vegetables) or protein or vegetable or "Pantry"
    sauce = _sauce_for_cuisine(cuisine)
    strategies = [
        {"strategy": "quick_bowl", "label": "Quick Bowl", "title": f"{cuisine} {base} Bowl" if foundation else f"{cuisine} {base} Dinner Bowl", "energy": "Very Low", "energy_rank": 0, "budget": "Budget", "budget_rank": 1, "why": "fastest low-energy assembly when components are already easy or prepared"},
        {"strategy": "skillet", "label": "Skillet", "title": f"{cuisine} {base} Skillet", "energy": "Low", "energy_rank": 1, "budget": "Budget", "budget_rank": 1, "why": "one pan, flexible texture"},
        {"strategy": "soup", "label": "Soup", "title": f"{cuisine} {base} Soup", "energy": "Low", "energy_rank": 1, "budget": "Budget", "budget_rank": 1, "why": "soft, stretchable, and forgiving"},
        {"strategy": "handheld", "label": "Handheld", "title": f"{cuisine} {base} Wrap or Sandwich", "energy": "Low", "energy_rank": 1, "budget": "Budget", "budget_rank": 1, "why": "good when standing/eating energy is limited"},
        {"strategy": "plate", "label": "Plate", "title": f"{cuisine} {base} Plate", "energy": "Low", "energy_rank": 1, "budget": "Moderate", "budget_rank": 2, "why": "simple meat/veg/foundation serving"},
        {"strategy": "casserole", "label": "Casserole", "title": f"{cuisine} {base} {foundation} Casserole" if foundation else f"{cuisine} {base} Casserole", "energy": "Medium", "energy_rank": 2, "budget": "Budget", "budget_rank": 1, "why": "family-style and good for leftovers"},
        {"strategy": "kid_adventure", "label": "Kid Adventure", "title": f"{base} Adventure Plate", "energy": "Very Low", "energy_rank": 0, "budget": "Budget", "budget_rank": 1, "why": "playful plating and familiar components"},
    ]

    candidates = []
    for s in strategies:
        c = dict(s)
        c.update({
            "sauce": sauce,
            "protein": protein,
            "vegetable": vegetable,
            "vegetables": vegetables,
            "foundation": foundation,
            "cuisine": cuisine,
            "servings": servings,
        })
        if not foundation and c["strategy"] in {"quick_bowl", "casserole"}:
            c["score_penalty_note"] = "missing foundation"
        score, plan = _score_candidate(c, energy_level, budget_level, time_limit)
        if not foundation and c["strategy"] in {"quick_bowl", "casserole"}:
            score = max(0, score - 8)
        c["score"] = score
        c["minutes"] = plan["total_minutes"]
        c["active_minutes"] = plan["active_minutes"]
        c["passive_minutes"] = plan["passive_minutes"]
        c["attention_score"] = plan["attention_score"]
        c["energy_fit"] = plan["energy_fit"]
        candidates.append(c)

    candidates.sort(key=lambda x: (x["score"], -x["active_minutes"], -x["passive_minutes"]), reverse=True)
    return candidates[:max_results]


def build_recipe_from_candidate(candidate):
    protein = candidate.get("protein", "")
    vegetables = _as_list(candidate.get("vegetables") if candidate.get("vegetables") is not None else candidate.get("vegetable", ""))
    foundation = candidate.get("foundation", "")
    instructions = generate_human_instructions(candidate)
    plan_summary = build_plan_summary(candidate)

    summary = (
        f"{candidate.get('label')} · {candidate.get('energy')} energy · {candidate.get('budget')} · "
        f"{plan_summary['total_minutes']} min total · {plan_summary['active_minutes']} min active · "
        f"{plan_summary['passive_minutes']} min passive · attention {plan_summary['attention_score']}/10 · "
        f"down-day fit {plan_summary['energy_fit']} · serves {candidate.get('servings', 4)}"
    )

    return {
        "name": candidate.get("title", "Generated Meal"),
        "instructions": [line for line in instructions.split("\n") if line.strip()],
        "grocery_list": _unique([protein] + vegetables + [foundation]),
        "servings": candidate.get("servings", 4),
        "summary": summary,
        "plan_summary": plan_summary,
    }


def build_simple_meal(protein_name, vegetable_name, foundation_name, sauce_name="", flavor_name="", meal_template=""):
    return build_recipe_from_candidate(
        generate_candidates(protein_name, vegetable_name, foundation_name, flavor_name or "Comfort Food", "Low", "Budget", 30, 4, 1)[0]
    )
