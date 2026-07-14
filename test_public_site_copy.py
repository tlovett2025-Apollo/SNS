from pathlib import Path


PUBLIC_FLOW = Path(__file__).parent / "web" / "public-site" / "sns-flow.js"


def test_recipe_fallback_uses_kitchen_language_instead_of_engine_jargon():
    public_copy = PUBLIC_FLOW.read_text(encoding="utf-8").lower()

    assert "longest-lead" not in public_copy
    assert "extra cooking time" in public_copy
