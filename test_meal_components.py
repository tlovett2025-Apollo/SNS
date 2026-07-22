"""Golden contracts for reusable meal-component recognition."""

from meal_components import (
    component_by_archetype,
    recognize_meal_components,
    suggest_known_sides,
)
from recipe_engine import build_recipe_from_candidate, generate_candidates


def component_candidate(foundation, available):
    return {
        "protein": "Chicken thighs",
        "protein_state": "Fresh Raw",
        "vegetable": "",
        "foundation": foundation,
        "inventory_have": available,
        "selected_extras": [],
        "cooking_method": "skillet",
        "meal_structure": "composed_plate",
    }


def test_pasta_cheese_and_milk_capabilities_recognize_mac_and_cheese():
    plan = recognize_meal_components(component_candidate(
        "Pasta", ["Pasta", "Mozzarella cheese", "Milk"],
    )).to_dict()
    side = next(item for item in plan["components"] if item["role"] == "side")

    assert side["archetype"] == "macaroni_and_cheese"
    assert side["method"] == "boil_then_cheese_sauce"
    assert {item["job"] for item in side["ingredients"]} == {
        "pasta", "cheese", "sauce_liquid",
    }


def test_pasta_without_cheese_remains_a_plain_prepared_side():
    plan = recognize_meal_components(component_candidate(
        "Macaroni", ["Macaroni", "Milk", "Butter"],
    )).to_dict()
    side = next(item for item in plan["components"] if item["role"] == "side")
    assert side["archetype"] == "prepared_side"


def test_recognized_mac_and_cheese_compiles_to_a_separate_side_component():
    candidate = generate_candidates(
        "Chicken thighs", "", "Macaroni", "BBQ", "High", "Budget", 60, 2, 1,
        protein_state="Fresh Raw",
        available_items=[
            "Chicken thighs", "Macaroni", "Butter", "BBQ sauce", "Garlic powder",
            "Onion powder", "Black pepper", "Cheddar cheese",
        ],
        available_equipment=["Oven", "Stovetop"],
        requested_method="skillet", meal_structure="composed_plate",
    )[0]
    recipe = build_recipe_from_candidate(candidate)
    actions = " ".join(recipe["action_steps"])
    component = component_by_archetype(candidate, "macaroni_and_cheese")

    assert component
    assert "Return the drained Macaroni to its pot" in actions
    assert "add Cheddar cheese gradually" in actions
    assert "serve Macaroni and cheese alongside" in actions
    assert "Stir Cheddar cheese into the skillet" not in actions
    assert any(item.get("component_job") == "cheese" for item in recipe["inventory_requirements"])
    assert recipe["component_plan"]["components"]


def test_component_method_contract_can_distinguish_main_from_side_environment():
    candidate = component_candidate("Macaroni", ["Macaroni", "Cheddar cheese", "Milk"])
    candidate["component_methods"] = {"main": "oven"}
    plan = recognize_meal_components(candidate).to_dict()
    main = next(item for item in plan["components"] if item["role"] == "main")
    side = next(item for item in plan["components"] if item["role"] == "side")

    assert main["method"] == "oven"
    assert "oven" in main["equipment"]
    assert side["method"] == "boil_then_cheese_sauce"


def test_known_side_suggestions_are_selection_recipes_not_generated_meals():
    suggestions = suggest_known_sides(
        ["Macaroni", "Cheddar cheese", "Milk", "Broccoli", "Bread"],
        ["Macaroni", "Bread"], ["Broccoli"],
        protein="Chicken breast", equipment_names=["Stovetop", "Oven"],
    )
    by_archetype = {item["archetype"]: item for item in suggestions}

    macaroni = by_archetype["macaroni_and_cheese"]
    assert macaroni["selection"]["foundation"] == "Macaroni"
    assert set(macaroni["selection"]["extras"]) == {"Cheddar cheese", "Milk"}
    assert macaroni["uses_only_kitchen_items"] is True
    assert by_archetype["steamed_vegetable_side"]["selection"] == {"produce": ["Broccoli"]}
    assert by_archetype["warmed_bread_side"]["selection"]["foundation"] == "Bread"
