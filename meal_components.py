"""Reusable meal-component recognition for Stock & Stir.

Ingredient KOs describe what ingredients can do. Component archetypes describe
what those capabilities can become together. The planner consumes this contract
instead of accumulating ingredient-name combinations.
"""

from dataclasses import asdict, dataclass, field
from typing import Iterable

from ingredient_profiles import get_ingredient_profile


def _clean(value) -> str:
    return "" if value is None else str(value).strip()


def _key(value) -> str:
    return " ".join(_clean(value).lower().replace("-", " ").split())


@dataclass(frozen=True)
class ComponentIngredient:
    name: str
    job: str
    source: str = "selected"
    quantity: str = ""


@dataclass(frozen=True)
class ComponentPlan:
    component_id: str
    archetype: str
    name: str
    role: str
    method: str
    ingredients: tuple[ComponentIngredient, ...]
    equipment: tuple[str, ...] = ()
    outcome: str = ""
    knowledge_source: str = "component_archetype"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MealComponentPlan:
    structure: str
    components: tuple[ComponentPlan, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "structure": self.structure,
            "components": [component.to_dict() for component in self.components],
        }


def _has_family(name: str, family_code: str, role: str = "ingredient") -> bool:
    return family_code in set(
        get_ingredient_profile(name, role).behavior_family_codes
    )


def _first_with_family(names: Iterable[str], family_code: str) -> str:
    return next((name for name in names if _has_family(name, family_code)), "")


def recognize_meal_components(candidate: dict) -> MealComponentPlan:
    """Recognize producible components from selected food and pantry capabilities."""
    available = list(dict.fromkeys([
        *[_clean(item) for item in candidate.get("inventory_have") or []],
        *[_clean(item) for item in candidate.get("selected_extras") or []],
    ]))
    foundation = _clean(candidate.get("foundation"))
    protein = _clean(candidate.get("protein"))
    vegetables = [
        _clean(item) for item in _clean(candidate.get("vegetable")).split(" & ")
        if _clean(item)
    ]
    components = []

    if protein:
        main_method = _clean(
            (candidate.get("component_methods") or {}).get("main")
            or candidate.get("cooking_method") or candidate.get("strategy")
        )
        main_equipment = {
            "skillet": ("12-inch skillet",),
            "oven": ("rimmed sheet pan or baking dish", "oven"),
            "grill": ("outdoor grill",),
            "air_fryer": ("air fryer basket",),
        }.get(main_method, ())
        components.append(ComponentPlan(
            "main-protein", "cooked_protein", protein, "main",
            main_method,
            (ComponentIngredient(protein, "primary"),),
            main_equipment,
            outcome="Safely cooked main protein with method-appropriate texture.",
            knowledge_source="ingredient_ko",
        ))

    if vegetables:
        components.append(ComponentPlan(
            "vegetables", "vegetable_component", " & ".join(vegetables), "vegetable",
            "method_selected_by_relationships",
            tuple(ComponentIngredient(name, "vegetable") for name in vegetables),
            outcome="Vegetables cooked to compatible, observable doneness.",
            knowledge_source="ingredient_relationships",
        ))

    if foundation:
        cheese = _first_with_family(available, "melting_cheese")
        milk = _first_with_family(available, "milk_cream")
        butter = _first_with_family(available, "cooking_fat")
        is_pasta = _has_family(foundation, "pasta", "foundation")
        is_bread_side = (
            _has_family(foundation, "bread_wrap", "foundation")
            and _clean(candidate.get("cooking_method")) != "handheld"
        )
        if is_pasta and cheese and (milk or butter):
            helpers = [
                ComponentIngredient(foundation, "pasta"),
                ComponentIngredient(cheese, "cheese", "pantry_helper", "1 cup shredded"),
            ]
            if milk:
                helpers.append(ComponentIngredient(milk, "sauce_liquid", "pantry_helper", "1/2 cup"))
            if butter:
                helpers.append(ComponentIngredient(butter, "sauce_fat", "pantry_helper", "1 tablespoon"))
            components.append(ComponentPlan(
                "side-macaroni-and-cheese", "macaroni_and_cheese",
                "Macaroni and cheese", "side", "boil_then_cheese_sauce",
                tuple(helpers),
                ("large saucepan or pot", "colander", "wooden spoon or whisk"),
                "Tender pasta coated in a smooth cheese sauce.",
            ))
        elif is_bread_side:
            components.append(ComponentPlan(
                "side-warmed-bread", "warmed_bread_side", foundation, "side",
                "warm_in_oven", (ComponentIngredient(foundation, "bread_side"),),
                ("small sheet pan", "oven"),
                "Warm bread served alongside without becoming the meal base.",
            ))
        else:
            components.append(ComponentPlan(
                "side-foundation", "prepared_side", foundation, "side",
                "ingredient_ko_method", (ComponentIngredient(foundation, "side"),),
                outcome="Prepared side ready to serve with the main component.",
                knowledge_source="ingredient_ko",
            ))

    return MealComponentPlan(
        _clean(candidate.get("meal_structure")) or "integrated",
        tuple(components),
    )


def component_by_archetype(candidate: dict, archetype: str) -> dict | None:
    plan = candidate.get("component_plan") or {}
    return next((
        component for component in plan.get("components") or []
        if component.get("archetype") == archetype
    ), None)


def suggest_known_sides(
    inventory_names: Iterable[str],
    foundation_names: Iterable[str],
    produce_names: Iterable[str],
    *,
    protein: str = "",
    equipment_names: Iterable[str] = (),
    limit: int = 5,
) -> list[dict]:
    """Return producible, trained side components for a selected main.

    Suggestions are selection recipes, not generated meal recipes. Each card
    declares the exact builder selections that reproduce the known component.
    """
    inventory = list(dict.fromkeys(_clean(item) for item in inventory_names if _clean(item)))
    owned = {_key(item) for item in inventory}
    foundations = [item for item in foundation_names if _key(item) in owned]
    produce = [item for item in produce_names if _key(item) in owned]
    equipment = {_key(item) for item in equipment_names if _clean(item)}
    suggestions: list[dict] = []

    def add(
        side_id: str, archetype: str, name: str, ingredients: list[str],
        selection: dict, method: str, equipment_needed: list[str], description: str,
    ) -> None:
        suggestions.append({
            "side_id": side_id,
            "archetype": archetype,
            "name": name,
            "description": description,
            "ingredients": ingredients,
            "selection": selection,
            "method": method,
            "equipment": equipment_needed,
            "uses_only_kitchen_items": all(_key(item) in owned for item in ingredients),
            "for_protein": _clean(protein),
        })

    cheese = _first_with_family(inventory, "melting_cheese")
    milk = _first_with_family(inventory, "milk_cream")
    fat = _first_with_family(inventory, "cooking_fat")
    pasta = next((item for item in foundations if _has_family(item, "pasta", "foundation")), "")
    if pasta and cheese and (milk or fat):
        helpers = [cheese, *([milk] if milk else []), *([fat] if fat else [])]
        add(
            "known-macaroni-and-cheese", "macaroni_and_cheese", "Macaroni and cheese",
            [pasta, *helpers], {"foundation": pasta, "extras": helpers},
            "boil_then_cheese_sauce", ["stovetop", "large saucepan or pot"],
            "Boil the pasta, then finish it as a creamy cheese side in the same pot.",
        )

    steamable = [
        item for item in produce
        if "steam-friendly" in set(get_ingredient_profile(item, "vegetable").physical_traits)
    ]
    if steamable:
        chosen = steamable[:2]
        add(
            "known-steamed-vegetables", "steamed_vegetable_side",
            "Steamed " + " and ".join(chosen), chosen, {"produce": chosen},
            "steam", ["stovetop", "covered pot", "steamer basket preferred"],
            "Steam compatible vegetables together and stop at crisp-tender.",
        )

    bread = next((
        item for item in foundations if _has_family(item, "bread_wrap", "foundation")
    ), "")
    if bread:
        method = "warm_in_oven" if any("oven" in item for item in equipment) else "warm"
        add(
            "known-warmed-bread", "warmed_bread_side", f"Warm {bread}", [bread],
            {"foundation": bread}, method,
            ["oven", "small sheet pan"] if method == "warm_in_oven" else ["warming vessel"],
            "Warm the bread separately and serve it alongside the main.",
        )

    plain_foundations = [
        item for item in foundations
        if item not in {pasta, bread}
        and not _has_family(item, "bread_wrap", "foundation")
    ]
    for item in plain_foundations:
        behavior = get_ingredient_profile(item, "foundation")
        family = next(iter(sorted(behavior.behavior_family_codes)), "prepared_side")
        label = f"{item} side"
        add(
            f"known-{_key(item).replace(' ', '-')}", f"prepared_{family}_side", label,
            [item], {"foundation": item}, "ingredient_ko_method", ["method-appropriate vessel"],
            f"Prepare {item} by its trained package or ingredient method and serve it alongside.",
        )
        if len(suggestions) >= limit:
            break

    return suggestions[:limit]
