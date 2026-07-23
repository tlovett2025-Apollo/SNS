from pathlib import Path


PUBLIC_FLOW = Path(__file__).parent / "web" / "public-site" / "sns-flow.js"


def test_recipe_failures_are_visible_and_never_fabricate_a_recipe():
    public_copy = PUBLIC_FLOW.read_text(encoding="utf-8")

    assert "fallbackRecipes" not in public_copy
    assert "fallbackBuilderOptions" not in public_copy
    assert "Gather the selected ingredients and the equipment you need." not in public_copy
    assert "This recipe could not load." in public_copy
    assert "Meal ideas could not load." in public_copy
    assert "data-retry-recipes" in public_copy


def test_recipe_feedback_records_ok_or_ng_and_shows_dialog_errors():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    recipe_page = (PUBLIC_FLOW.parent / "recipe.html").read_text(encoding="utf-8")

    assert "data-recipe-looks-right" in recipe_page
    assert "Recipe looks right" in recipe_page
    assert "data-recipe-report-dialog-status" in recipe_page
    assert 'reportPayload("OK", ["recipe_ok"])' in flow
    assert 'reportPayload(' in flow
    assert '"NG",' in flow
    assert "dialogStatus.textContent = message" in flow


def test_my_kitchen_supports_add_remove_equipment_and_browser_persistence():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")

    assert "localStorage.setItem(kitchenStorageKey" in flow
    assert "+ Add equipment" in flow
    assert "data-remove-food" in flow
    assert "data-kitchen-dialog" in kitchen_page


def test_accounts_use_supabase_and_migrate_the_browser_kitchen_once():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    auth = (PUBLIC_FLOW.parent / "sns-auth.js").read_text(encoding="utf-8")
    config = (PUBLIC_FLOW.parent / "sns-config.js").read_text(encoding="utf-8")
    login = (PUBLIC_FLOW.parent / "login.html").read_text(encoding="utf-8")
    preferences = (PUBLIC_FLOW.parent / "household-preferences.html").read_text(encoding="utf-8")

    assert "signInWithPassword" in auth
    assert "resetPasswordForEmail" in auth
    assert "persistSession: true" in auth
    assert "callback(currentSession, event)" in auth
    assert "sb_publishable_" in config
    assert "service_role" not in config
    assert "snsAuthPrototype" not in login
    assert "snsKitchenMigrated:" in flow
    assert "Move them into your shared Stock & Stir kitchen" in flow
    assert "snsKitchenStateV2:${userId}" in flow
    assert "kitchenDraftKey(sharedKitchenSync.userId)" in flow
    assert "saved-as-draft" in flow
    assert "saving is disabled" in flow
    assert "Saved in this browser; API connection is pending." not in flow
    assert 'event === "SIGNED_IN"' in flow
    assert "friendlyAuthError" in login
    assert "Do not keep clicking it" in login
    assert 'myKitchen: endpoint("/api/MyKitchen")' in flow
    assert "Authorization: `Bearer ${token}`" in flow
    assert 'data-preference-type="allergy"' in preferences
    assert "An empty box means no allergies are saved" in preferences
    assert 'placeholder="Type allergies here"' in preferences
    assert "Peanuts, shellfish" not in preferences
    assert 'data-preference-type="exclusion"' in preferences


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
    assert "function installInventoryContracts(contracts)" in flow
    assert "?include_contracts=true" in flow
    assert "allowed_units" in flow


def test_my_kitchen_uses_compact_rows_and_a_phone_first_accordion():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    css = (PUBLIC_FLOW.parent / "sns-flow.css").read_text(encoding="utf-8")

    assert "function initializeKitchenAccordion()" in flow
    assert 'other.classList.add("collapsed")' in flow
    assert "<summary>More details</summary>" in flow
    assert "grid-template-columns:minmax(150px,1fr) minmax(270px,360px) auto" in css
    assert "@media(max-width:760px)" in css
    assert "grid-column:1/-1;grid-row:2" in css
    assert '"ribeye": "Ribeye steak"' in flow
    assert '"corn starch": "Cornstarch"' in flow


def test_my_kitchen_can_preview_merge_replace_and_undo_sample_or_csv_imports():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")
    sample_data = (PUBLIC_FLOW.parent / "sample-pantries.js").read_text(encoding="utf-8")
    css = (PUBLIC_FLOW.parent / "sns-flow.css").read_text(encoding="utf-8")

    assert 'script src="sample-pantries.js"' in kitchen_page
    assert "data-open-pantry-import" in kitchen_page
    assert "data-pantry-csv" in kitchen_page
    assert "Merge with My Kitchen" in kitchen_page
    assert "Replace My Kitchen" in kitchen_page
    assert "data-confirm-custom-items" in kitchen_page
    assert "data-undo-pantry-import" in kitchen_page
    assert "function parseCsv(text)" in flow
    assert "function normalizeImportRows" in flow
    assert "function applyImportedPantry" in flow
    assert "kitchenImportUndoKey" in flow
    assert "window.SNS_SAMPLE_PANTRIES" in sample_data
    assert '"Pacific Northwest"' in sample_data
    assert '"Florida & Caribbean-influenced"' in sample_data
    assert ".pantry-import-dialog" in css
    assert "max-height:96dvh" in css


def test_my_kitchen_capture_is_phone_first_reviewed_and_never_auto_saves_photos():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")
    css = (PUBLIC_FLOW.parent / "sns-flow.css").read_text(encoding="utf-8")
    blueprint = (PUBLIC_FLOW.parents[2] / "render.yaml").read_text(encoding="utf-8")

    assert 'data-open-inventory-capture="barcode"' in kitchen_page
    assert 'data-open-inventory-capture="photo"' in kitchen_page
    assert 'capture="environment"' in kitchen_page
    assert "Nothing is added automatically" in kitchen_page
    assert "Stock &amp; Stir does not save the photo" in kitchen_page
    assert 'resolveBarcode: endpoint("/api/ResolveBarcode")' in flow
    assert 'recognizePantryPhoto: endpoint("/api/RecognizePantryPhoto")' in flow
    assert "function pantryPhotoDataUrl(file)" in flow
    assert "function bindInventoryCapture()" in flow
    assert "@undecaf/barcode-detector-polyfill@0.9.23" in flow
    assert 'applyImportedPantry(items, "merge")' in flow
    assert ".inventory-capture-dialog" in css
    assert ".capture-item-fields" in css
    assert "max-height:96dvh" in css
    assert "OPENAI_API_KEY" in blueprint
    assert "sync: false" in blueprint
    assert "SNS_PANTRY_VISION_MODEL" in blueprint


def test_recipe_page_exposes_inventory_resolutions_and_preserves_substep_breaks():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    recipe_page = (PUBLIC_FLOW.parent / "recipe.html").read_text(encoding="utf-8")
    css = (PUBLIC_FLOW.parent / "sns-flow.css").read_text(encoding="utf-8")

    assert "data-kitchen-check" in recipe_page
    assert '["Need", "Short"].includes(item?.status)' in flow
    assert '["Substitute", "Omit"].includes(item?.status)' in flow
    assert "item.omission_consequence" in flow
    assert "item.resolved_name" in flow
    assert "data-grocery-list" in recipe_page
    assert "ingredientQuantity" in flow
    assert "white-space: pre-wrap" in css
    assert "data-recipe-work-time" in recipe_page
    assert "total minutes" in flow
    assert "mostly waiting" in flow
    assert "Report this recipe" in recipe_page
    assert 'reportRecipe: endpoint("/api/ReportRecipe")' in flow
    assert "recipe_snapshot: recipe" in flow
    assert "rendered_recipe_text" in flow


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
    assert "Choose everything in one place" in builder_page
    assert "Chosen for this meal" in builder_page
    assert "data-catalog-filter=\"vegetable\"" in builder_page
    assert "data-catalog-filter=\"fruit\"" in builder_page
    assert "data-catalog-filter=\"canned\"" in builder_page
    assert "data-catalog-filter=\"spice\"" in builder_page
    assert "data-catalog-scope=\"owned\"" in builder_page
    assert "data-catalog-scope=\"all\"" in builder_page
    assert 'scope === "all" || button.dataset.owned === "true"' in flow
    assert 'data-catalog-filter="owned"' not in builder_page
    assert "options.meal_structures" in flow
    assert "options.methods" in flow
    assert "data-protein-search" not in builder_page
    assert "data-browse-catalog" not in builder_page
    assert ".produce-choice[hidden]" in (PUBLIC_FLOW.parent / "sns-flow.css").read_text(encoding="utf-8")
    assert '>Canned</option>' in flow
    assert 'item.id' in flow
    assert 'input[name="extras"]:checked' in flow
    assert "Cold <small>training next" in builder_page
    assert "How should the finished meal come together?" in builder_page
    assert 'label="Planning ahead"' in builder_page
    assert '<option value="240">4 hours</option>' in builder_page
    assert "body.detail || body.message" in flow


def test_my_kitchen_keeps_whole_and_thin_sliced_chicken_distinct():
    kitchen_page = (PUBLIC_FLOW.parent / "my-kitchen.html").read_text(encoding="utf-8")

    assert 'data-food="Chicken breast" data-form="Fresh Raw"' in kitchen_page
    assert 'data-food="Chicken breast" data-form="Thin-sliced Raw"' in kitchen_page
    assert "Chicken breast slices" in kitchen_page


def test_builder_uses_one_catalog_for_owned_and_purchase_ingredients():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    builder_page = (PUBLIC_FLOW.parent / "build-your-meal.html").read_text(encoding="utf-8")
    recipe_page = (PUBLIC_FLOW.parent / "recipe.html").read_text(encoding="utf-8")

    assert "Your kitchen items appear first" in builder_page
    assert "data-open-ingredient-catalog" in builder_page
    assert "data-ingredient-catalog" in builder_page
    assert "data-catalog-options" in builder_page
    assert 'data-owned="${isOwned}"' in flow
    assert "const catalogItems" in flow
    assert ".filter(item => !(item.owned" not in flow
    assert "selectedPurchaseNames" in flow
    assert "Added to this meal’s grocery list" in builder_page
    assert "Everything this recipe needs that is not currently in My Kitchen." in recipe_page
    assert "data-recipe-equipment" in recipe_page
    assert "recipe.equipment" in flow


def test_builder_offers_known_sides_after_the_main_is_chosen():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")
    builder_page = (PUBLIC_FLOW.parent / "build-your-meal.html").read_text(encoding="utf-8")

    assert "Choose a side—or two" in builder_page
    assert "data-side-suggestion-options" in builder_page
    assert "/api/GetKnownSideSuggestions" in flow
    assert "Choose no more than two sides" in flow
    assert 'side_components: [...form.querySelectorAll(\'input[name="known-side"]:checked\')]' in flow


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
    assert "A chosen side may use its own trained vessel or heat source" in builder_page
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


def test_every_page_can_read_the_server_owned_inventory_shape():
    flow = PUBLIC_FLOW.read_text(encoding="utf-8")

    assert "saved.foods || saved.inventory || saved.inventory_lots || []" in flow


def test_app_pages_cache_bust_shared_assets_as_one_release():
    pages = [
        "home.html", "my-kitchen.html", "build-your-meal.html", "choose-recipe.html",
        "recipe.html", "favorite-recipes.html", "signature-recipes.html",
        "household-preferences.html", "kitchen-training.html", "pantry-101.html",
    ]
    for name in pages:
        page = (PUBLIC_FLOW.parent / name).read_text(encoding="utf-8")
        assert "sns-flow.css?v=20260723c2" in page
        assert "sns-flow.js?v=20260723c2" in page
