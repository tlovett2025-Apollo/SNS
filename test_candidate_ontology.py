from recipe_engine import (
    _experience_overlays,
    _method_is_eligible,
    _serving_styles,
)


def test_plate_and_bowl_are_serving_styles_not_cooking_methods():
    assert _serving_styles("skillet") == ["plate", "bowl"]
    assert _serving_styles("casserole") == ["plate", "bowl"]
    assert _serving_styles("soup") == ["bowl", "cup"]
    assert _serving_styles("braise") == ["plate", "bowl"]


def test_handheld_requires_a_wrapper_or_bread():
    assert not _method_is_eligible("handheld", ["Chicken", "Mushrooms"], "", [])
    assert _method_is_eligible("handheld", ["Chicken", "Tortillas"], "", [])
    assert _method_is_eligible("handheld", ["Chicken", "Bread"], "", [])


def test_soup_requires_a_liquid_path_or_an_inherently_stewable_protein():
    assert not _method_is_eligible("soup", ["Chicken", "Carrots"], "", [])
    assert _method_is_eligible("soup", ["Chicken", "Chicken broth"], "", [])
    assert _method_is_eligible("soup", ["Chicken", "Cream of chicken soup"], "", [])
    assert _method_is_eligible(
        "soup", ["Beef stew meat", "Potatoes", "Carrots"], "", []
    )


def test_long_braise_requires_a_collagen_rich_protein():
    assert _method_is_eligible("braise", ["Beef brisket", "Pinto beans"], "", [])
    assert not _method_is_eligible("braise", ["Chicken breast", "Pinto beans"], "", [])


def test_casserole_requires_structure():
    assert not _method_is_eligible("casserole", ["Chicken", "Mushrooms"], "", [])
    assert _method_is_eligible("casserole", ["Chicken", "Mushrooms"], "Rice", [])
    assert _method_is_eligible("casserole", ["Chicken breast", "Cheddar cheese"], "", [])


def test_grill_requires_available_grill_equipment():
    assert not _method_is_eligible("grill", ["Chicken"], "", ["Oven", "Stovetop"])
    assert _method_is_eligible("grill", ["Chicken"], "", ["Outdoor Grill"])


def test_kid_adventure_is_an_overlay_on_the_same_meal():
    assert _experience_overlays(False) == []
    overlays = _experience_overlays(True, "dinosaurs")
    assert overlays == [{
        "type": "kid_adventure",
        "theme": "dinosaurs",
        "same_meal": True,
        "include_fun_facts": True,
        "include_conversation_prompts": True,
    }]
