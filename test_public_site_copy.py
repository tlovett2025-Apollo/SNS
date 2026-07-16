from pathlib import Path


PUBLIC_FLOW = Path(__file__).parent / "web" / "public-site" / "sns-flow.js"


def test_recipe_fallback_uses_kitchen_language_instead_of_engine_jargon():
    public_copy = PUBLIC_FLOW.read_text(encoding="utf-8").lower()

    assert "longest-lead" not in public_copy
    assert "extra cooking time" in public_copy


def test_my_kitchen_supports_add_remove_equipment_and_browser_persistence():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")

    assert "localStorage.setItem(kitchenStorageKey" in flow
    assert "+ Add equipment" in flow
    assert "data-remove-food" in flow
    assert "data-kitchen-dialog" in kitchen_page


def test_my_kitchen_uses_real_quantities_and_units_for_countable_food():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")

    assert "data-dialog-quantity" in kitchen_page
    assert "data-dialog-unit" in kitchen_page
    assert 'data-food="Lasagna noodles"' in kitchen_page
    assert '"lasagna noodles": { unit: "box"' in flow
    assert "function quantityStepForUnit(unit)" in flow
    assert "addQuantity.step = quantityStepForUnit(addUnit.value)" in flow
    assert "data-kitchen-dialog-form novalidate" in kitchen_page
    assert "quantity," in flow
    assert "unit:" in flow


def test_recipe_page_exposes_inventory_resolutions_and_preserves_substep_breaks():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    recipe_page = (PUBLIC_FLOW.parent / "recipe.html").read_text(encoding="utf-8")
    css = (PUBLIC_FLOW.parent / "sns-flow.css").read_text(encoding="utf-8")

    assert "data-kitchen-check" in recipe_page
    assert '["Need", "Substitute", "Omit"].includes(item?.status)' in flow
    assert "item.omission_consequence" in flow
    assert "item.resolved_name" in flow
    assert "white-space: pre-wrap" in css


def test_build_your_meal_is_a_direct_shared_engine_path():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")
    builder_page = (PUBLIC_FLOW.parent / "build-your-meal.html").read_text(encoding="utf-8")

    assert "data-build-meal" in kitchen_page
    assert "Build Your Meal" in kitchen_page
    assert 'mode: "build_your_meal"' in flow
    assert "await requestRecipe(candidate.candidate_id" in flow
    assert "One protein for now" in builder_page
    assert "Vegetables &amp; fruit" in builder_page
    assert "Cold <small>training next" in builder_page
    assert "plate or in a bowl" in builder_page
