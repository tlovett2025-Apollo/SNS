"""Golden contracts for reusable meal-component recognition."""

import unittest

from meal_components import (
    component_by_archetype,
    ingredient_job,
    recognize_meal_components,
    suggest_known_sides,
)
from recipe_engine import build_recipe_from_candidate, generate_candidates
from side_archetypes import INGREDIENT_JOBS, SIDE_ACTIVITY_TEMPLATES, SIDE_ARCHETYPES


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


class MealComponentTests(unittest.TestCase):

 def test_pasta_cheese_and_milk_capabilities_recognize_mac_and_cheese(self):
    plan = recognize_meal_components(component_candidate(
        "Pasta", ["Pasta", "Mozzarella cheese", "Milk"],
    )).to_dict()
    side = next(item for item in plan["components"] if item["role"] == "side")

    assert side["archetype"] == "macaroni_and_cheese"
    assert side["method"] == "boil_then_cheese_sauce"
    assert {item["job"] for item in side["ingredients"]} == {
        "pasta", "cheese", "sauce_liquid",
    }


 def test_pasta_without_cheese_remains_a_plain_prepared_side(self):
    plan = recognize_meal_components(component_candidate(
        "Macaroni", ["Macaroni", "Milk", "Butter"],
    )).to_dict()
    side = next(item for item in plan["components"] if item["role"] == "side")
    assert side["archetype"] == "prepared_side"


 def test_recognized_mac_and_cheese_compiles_to_a_separate_side_component(self):
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


 def test_component_method_contract_can_distinguish_main_from_side_environment(self):
    candidate = component_candidate("Macaroni", ["Macaroni", "Cheddar cheese", "Milk"])
    candidate["component_methods"] = {"main": "oven"}
    plan = recognize_meal_components(candidate).to_dict()
    main = next(item for item in plan["components"] if item["role"] == "main")
    side = next(item for item in plan["components"] if item["role"] == "side")

    assert main["method"] == "roast"
    assert "Oven" in main["equipment"]
    assert side["method"] == "boil_then_cheese_sauce"


 def test_known_side_suggestions_are_selection_recipes_not_generated_meals(self):
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
    assert by_archetype["steamed_vegetables"]["selection"] == {"produce": ["Broccoli"]}
    assert by_archetype["warmed_bread_side"]["selection"]["foundation"] == "Bread"


 def test_round_one_trains_fifteen_side_archetypes_as_data(self):
    assert len(SIDE_ARCHETYPES) == 15
    assert set(SIDE_ARCHETYPES) == set(SIDE_ACTIVITY_TEMPLATES)
    assert all(item.required_jobs for item in SIDE_ARCHETYPES.values())
    assert {"side_base", "vegetable", "aromatic", "acid", "heat"} <= set(INGREDIENT_JOBS)


 def test_ingredient_jobs_come_from_family_and_trained_item_knowledge(self):
    assert ingredient_job("Limes") == "acid"
    assert ingredient_job("Onions") == "aromatic"
    assert ingredient_job("Serranos") == "heat"
    assert ingredient_job("Cheddar cheese") == "cheese"


 def test_round_one_side_training_matrix_has_executable_knowledge(self):
    for archetype in sorted(SIDE_ARCHETYPES):
        with self.subTest(archetype=archetype):
            trained = SIDE_ARCHETYPES[archetype]
            template = SIDE_ACTIVITY_TEMPLATES[archetype]

            assert trained.method
            assert trained.equipment
            assert trained.outcome.endswith(".")
            assert trained.holdability in {"poor", "fair", "good", "excellent"}
            assert "{" in template and "}" in template


 def test_selected_sides_own_their_ingredients_before_a_braise_is_compiled(self):
    sides = [
        {
            "side_id": "known-pepper-onion-medley",
            "archetype": "pepper_onion_medley",
            "name": "Celery and Poblanos medley",
            "ingredients": ["Celery", "Poblanos"],
            "selection": {"produce": ["Celery", "Poblanos"]},
            "method": "saute",
        },
        {
            "side_id": "known-seasoned-beans",
            "archetype": "seasoned_beans",
            "name": "Seasoned Black beans",
            "ingredients": ["Black beans", "Garlic powder"],
            "selection": {
                "foundation": "Black beans", "extras": ["Garlic powder"],
            },
            "method": "simmer",
        },
    ]
    candidate = generate_candidates(
        "Beef brisket", "", "", "Comfort Food", "High", "Moderate", 240, 4, 1,
        vegetable_names=[
            "Acorn squash", "Artichokes", "Cabbage", "Celery", "Poblanos",
        ],
        protein_state="Frozen Raw",
        available_items=[
            "Beef brisket", "Acorn squash", "Artichokes", "Cabbage", "Celery",
            "Poblanos", "Black beans", "Garlic powder", "Onion powder",
            "Black pepper", "Chicken broth", "Butter", "Milk", "All-purpose flour",
        ],
        available_equipment=["Oven", "Stovetop"], requested_method="oven_braise",
        component_forms={
            "Acorn squash": "Fresh", "Artichokes": "Fresh", "Cabbage": "Fresh",
            "Celery": "Fresh", "Poblanos": "Fresh", "Black beans": "Canned",
        },
        selected_side_components=sides,
    )[0]
    recipe = build_recipe_from_candidate(candidate)
    plan = " ".join(recipe["instructions"])

    assert candidate["vegetable"] == "Acorn squash & Artichokes & Cabbage"
    assert candidate["foundation"] == ""
    assert "Add Celery & Poblanos around the meat" not in plan
    assert "Add Black beans" not in plan
    assert plan.count("Sauté Celery & Poblanos") == 1
    assert plan.count("Put Black beans in a small saucepan") == 1
    assert "Milk" not in plan
    assert "All-purpose flour" not in plan
    assert plan.index("Add Artichokes to the braise") < plan.index("Add Acorn squash to the braise")
    assert plan.index("Add Acorn squash to the braise") < plan.index("Add Cabbage to the braise")
    assert recipe["validation"]["production_ready"] is True
