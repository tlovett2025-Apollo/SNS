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
