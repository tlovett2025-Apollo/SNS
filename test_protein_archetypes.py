"""Round 2 coverage matrix for main-protein execution contracts."""

import unittest

from ko_behavior import resolve_behavior
from protein_archetypes import PROTEIN_CONTRACTS, method_for_main, protein_contract
from recipe_engine import build_recipe_from_candidate, generate_candidates


FAMILY_SAMPLES = {
    "ground_meat": ("Ground beef", "Fresh Raw"),
    "tough_meat": ("Beef brisket", "Fresh Raw"),
    "stew_cut": ("Beef stew meat", "Fresh Raw"),
    "poultry_piece": ("Chicken thighs", "Fresh Raw"),
    "fish_fillet": ("Salmon", "Fresh Raw"),
    "shellfish_quick": ("Shrimp", "Fresh Raw"),
    "sausage": ("Italian sausage", "Fresh Raw"),
    "plant_protein": ("Tofu", "Fresh"),
    "tender_steak": ("Sirloin steak", "Fresh Raw"),
    "pork_cut": ("Pork chops", "Fresh Raw"),
    "pork_roast": ("Pork loin", "Fresh Raw"),
    "whole_poultry": ("Whole chicken", "Fresh Raw"),
    "bacon": ("Bacon", "Fresh Raw"),
    "ready_protein": ("Rotisserie chicken", "Cooked"),
    "egg": ("Eggs", "Fresh Raw"),
    "ready_cured_meat": ("Pepperoni", "Cooked"),
}


class ProteinArchetypeTests(unittest.TestCase):

 def test_round_two_covers_every_trained_main_protein_family(self):
    assert set(PROTEIN_CONTRACTS) == set(FAMILY_SAMPLES)
    assert len(PROTEIN_CONTRACTS) == 16
    assert all(contract.safety_endpoint for contract in PROTEIN_CONTRACTS.values())
    assert all(contract.environment_methods for contract in PROTEIN_CONTRACTS.values())


 def test_each_family_resolves_every_declared_environment_method(self):
    for family_code in sorted(FAMILY_SAMPLES):
        name, form = FAMILY_SAMPLES[family_code]
        contract = PROTEIN_CONTRACTS[family_code]
        with self.subTest(family=family_code):
            assert protein_contract(name, form) == contract

        for environment, expected_method in contract.environment_methods:
            with self.subTest(family=family_code, environment=environment):
                assert method_for_main(name, form, environment) == expected_method
                behavior = resolve_behavior(name, "protein", form, expected_method)
                assert behavior.method is not None
                assert behavior.method.method == expected_method
                assert behavior.method.doneness_cue
                assert behavior.method.failure_mode
                assert behavior.method.recovery_hint


 def test_oven_roast_main_and_stovetop_mac_and_cheese_compile_separately(self):
    candidate = generate_candidates(
        "Chicken thighs", "", "Macaroni", "BBQ", "Medium", "Budget", 90, 2, 1,
        protein_state="Fresh Raw",
        available_items=[
            "Chicken thighs", "Macaroni", "Cheddar cheese", "Butter",
            "BBQ sauce", "Garlic powder", "Onion powder", "Black pepper",
        ],
        available_equipment=["Oven", "Stovetop"],
        requested_method="oven_roast", meal_structure="composed_plate",
    )[0]
    recipe = build_recipe_from_candidate(candidate)
    text = " ".join(recipe["instructions"])
    main = next(
        item for item in recipe["component_plan"]["components"]
        if item["role"] == "main"
    )

    assert candidate["cooking_method"] == "oven_roast"
    assert main["method"] == "roast"
    assert "Roast Chicken thighs at 400°F" in text
    assert "Return the drained Macaroni to its pot" in text
    assert "Do not turn the dry-roasted main into a braise" in text
    assert "Pour the measured BBQ braising liquid around" not in text
    assert recipe["equipment"].count("Oven") == 1
