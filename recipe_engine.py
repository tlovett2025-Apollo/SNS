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


def generate_candidates(protein_name="", vegetable_name="", foundation_name="", cuisine_name="", energy_level="", budget_level="", time_minutes=30, servings=4, max_results=10):
    protein = _clean(protein_name)
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
        c.update({"score": score, "sauce": sauce, "protein": protein, "vegetable": vegetable, "foundation": foundation, "cuisine": cuisine, "servings": servings})
        candidates.append(c)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:max_results]


def build_recipe_from_candidate(candidate):
    protein = candidate.get("protein", "")
    vegetable = candidate.get("vegetable", "")
    foundation = candidate.get("foundation", "")
    sauce = candidate.get("sauce", "")
    cuisine = candidate.get("cuisine", "")
    strategy = candidate.get("strategy", "")
    steps = []
    if strategy == "quick_bowl":
        if foundation: steps.append(f"Prepare {foundation} as the base.")
        if protein: steps.append(f"Heat or cook {protein} until safe and ready.")
        if vegetable: steps.append(f"Cook or warm {vegetable} until it reaches the texture you like.")
        steps.append(f"Use {sauce} to pull the {cuisine} direction together.")
        steps.append("Layer everything in bowls and serve.")
    elif strategy == "skillet":
        if protein: steps.append(f"Cook {protein} in a skillet until safe and browned where appropriate.")
        if vegetable: steps.append(f"Add {vegetable} and cook until softened.")
        if foundation: steps.append(f"Add prepared {foundation} and heat through.")
        steps.append(f"Stir in or season toward {sauce}.")
        steps.append("Simmer briefly until hot and cohesive.")
    elif strategy == "casserole":
        if foundation: steps.append(f"Prepare {foundation} so it is ready to combine.")
        if protein: steps.append(f"Cook {protein} until safe.")
        if vegetable: steps.append(f"Cook {vegetable} until softened.")
        steps.append(f"Combine {_join([protein, vegetable, foundation])} with {sauce}.")
        steps.append("Bake or heat until hot, cohesive, and ready to serve.")
    elif strategy == "soup":
        if vegetable: steps.append(f"Start {vegetable} in the pot and cook until it begins to soften.")
        if protein: steps.append(f"Add {protein} and cook until safe.")
        if foundation: steps.append(f"Add {foundation} plus enough liquid to make soup.")
        steps.append(f"Season toward {cuisine} using {sauce} as the flavor direction.")
        steps.append("Simmer until everything is hot and spoon-tender.")
    elif strategy == "handheld":
        if protein: steps.append(f"Prepare {protein} as the main filling.")
        if vegetable: steps.append(f"Add {vegetable} for texture and balance.")
        steps.append(f"Add {sauce}.")
        steps.append("Wrap, stack, or fold as a handheld meal.")
        if foundation: steps.append(f"Serve {foundation} as a side if it does not fit inside.")
    elif strategy == "kid_adventure":
        if protein: steps.append(f"Heat {protein} until hot and ready.")
        if vegetable: steps.append(f"Prepare {vegetable} as the adventure side.")
        if foundation: steps.append(f"Prepare {foundation} as the filling side.")
        steps.append(f"Serve {sauce} as the dip, lava pool, moat, or drizzle.")
        steps.append("Plate everything playfully and serve.")
        steps.append("Fun fact: real pterosaurs are extinct and were not dinosaurs, so DinoBites-style chicken is the near-enough dinner approximation.")
    else:
        if foundation: steps.append(f"Prepare {foundation}.")
        if protein: steps.append(f"Cook {protein} until safe.")
        if vegetable: steps.append(f"Cook {vegetable} until tender.")
        steps.append(f"Season toward {cuisine} with {sauce}.")
        steps.append("Combine and serve.")
    return {"name": candidate.get("title", "Generated Meal"), "instructions": steps, "grocery_list": _unique([protein, vegetable, foundation]), "servings": candidate.get("servings", 4), "summary": f"{candidate.get('label')} · {candidate.get('energy')} energy · {candidate.get('budget')} · {candidate.get('minutes')} min · serves {candidate.get('servings', 4)}"}


def build_simple_meal(protein_name, vegetable_name, foundation_name, sauce_name="", flavor_name="", meal_template=""):
    return build_recipe_from_candidate(generate_candidates(protein_name, vegetable_name, foundation_name, flavor_name or "Comfort Food", "Low", "Budget", 30, 4, 1)[0])
