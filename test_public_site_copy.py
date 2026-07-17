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
    assert "data-recipe-work-time" in recipe_page
    assert "total minutes" in flow
    assert "mostly waiting" in flow


def test_build_your_meal_is_a_direct_shared_engine_path():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")
    builder_page = (PUBLIC_FLOW.parent / "build-your-meal.html").read_text(encoding="utf-8")

    assert "Help Me Build My Meal" in flow
    assert "Give Me Meal Ideas" in flow
    assert "Signature Recipes" in flow
    assert 'link("build-your-meal.html", "Help Me Build My Meal"' in flow
    assert 'mode: "build_your_meal"' in flow
    assert "await requestRecipe(candidate.candidate_id" in flow
    assert "Choose one or more" in builder_page
    assert "Vegetables &amp; fruit" in builder_page
    assert "Pantry &amp; fridge extras" in builder_page
    assert "Composed Plate" in flow
    assert "Layered Bowl" in flow
    assert "Cooked Together" in flow
    assert 'label:"Stovetop"' in flow
    assert "data-protein-search" in builder_page
    assert '>Canned</option>' in flow
    assert 'id:"grill"' in flow
    assert 'input[name="extras"]:checked' in flow
    assert "Cold <small>training next" in builder_page
    assert "How should the finished meal come together?" in builder_page
    assert 'label="Planning ahead"' in builder_page
    assert '<option value="240">4 hours</option>' in builder_page
    assert "body.detail || body.message" in flow


def test_quantity_and_form_controls_cover_packages_cans_appetites_and_garlic():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")
    preferences_page = (PUBLIC_FLOW.parent / "household-preferences.html").read_text(encoding="utf-8")
    builder_page = (PUBLIC_FLOW.parent / "build-your-meal.html").read_text(encoding="utf-8")

    assert "data-opened-at" in flow
    assert "data-package-weight" in flow
    assert "refrigerated_after_opening" in flow
    assert "package: 0.25" in flow
    assert "can: 0.5" in flow
    assert "data-eaters-light" in builder_page
    assert "data-eaters-standard" in builder_page
    assert "data-eaters-big" in builder_page
    assert "data-use-all-cans" in builder_page
    assert "data-produce-form" in flow
    assert "which garlic" in flow.lower()
    assert "data-dialog-form-note" in kitchen_page
    assert "data-household-members" not in kitchen_page
    assert "data-add-household-member" not in kitchen_page
    assert "data-household-members" in preferences_page
    assert "data-add-household-member" in preferences_page
    assert "data-save-household" in preferences_page
    assert "household_members: members" in flow


def test_make_a_meal_exposes_effort_and_selection_context():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")

    assert "data-make-effort" in kitchen_page
    assert "Tonight’s effort" in kitchen_page
    assert 'mealHistoryKey = "snsMealHistoryV1"' in flow
    assert "recent_meals: recentMealHistory()" in flow
    assert "selection_badge" in flow
    assert "effort_label" in flow
    assert "data-expiration-date" in flow


def test_three_meal_paths_have_distinct_jobs():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    home_page = (PUBLIC_FLOW.parent / "home.html").read_text(encoding="utf-8")
    builder_page = (PUBLIC_FLOW.parent / "build-your-meal.html").read_text(encoding="utf-8")
    signature_page = (PUBLIC_FLOW.parent / "signature-recipes.html").read_text(encoding="utf-8")

    assert "Give Me Meal Ideas" in flow
    assert "Help Me Build My Meal" in flow
    assert "Signature Recipes" in flow
    assert "My Favorite Recipes" in home_page
    assert "Choose the cooking environment" in builder_page
    assert "meal structure, effort, liquid, and ingredient behavior" in builder_page
    assert "known recipe" in signature_page


def test_logged_in_home_and_left_navigation_are_connected():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    css = (PUBLIC_FLOW.parent / "sns-flow.css").read_text(encoding="utf-8")
    home_page = (PUBLIC_FLOW.parent / "home.html").read_text(encoding="utf-8")
    login_page = (PUBLIC_FLOW.parent / "login.html").read_text(encoding="utf-8")
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")

    assert "Welcome back" in home_page
    assert "Why a remembered pantry changes dinner" in home_page
    assert "installAppShell()" in flow
    assert "Pantry 101" in flow
    assert "Kitchen Training" in flow
    assert "Household Preferences" in flow
    assert "data-save-kitchen" in flow
    assert "app-sidebar" in css
    assert "position:fixed" in css
    assert 'data-app-shell' in kitchen_page
    assert 'location.href = "home.html"' in login_page


def test_meal_navigation_opens_destinations_before_waiting_for_api():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    home_page = (PUBLIC_FLOW.parent / "home.html").read_text(encoding="utf-8")

    assert 'choose-recipe.html?refresh=1' in flow
    assert 'choose-recipe.html?refresh=1' in home_page
    assert 'href="build-your-meal.html"' in home_page
    assert 'Finding genuinely different ideas from My Kitchen' in flow
    assert 'if (currentPage() !== "choose-recipe.html") return' in flow
